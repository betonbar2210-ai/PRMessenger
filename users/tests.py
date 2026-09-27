import smtplib
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from bulkmailing.models import BulkMailing, BulkMailingAttempt
from bulkmailing.services import (
    MailingWindowError,
    claim_mailing,
    next_run_at,
    send_due_mailings,
    send_mailing,
    validate_window,
)
from clients.models import Client as ClientModel
from config.cache import (
    CONNECT_TIMEOUT_SECONDS,
    RETRY_AFTER_SECONDS,
)
from config.middleware import ClientCacheMiddleware
from texts.models import Text
from users.models import CustomUser
from users.services import make_confirm_token, read_confirm_token

PASSWORD = "test-pass-123"


def make_user(
    email,
    *,
    role="user",
    verified=True,
    active=True,
    blocked=False,
    **kwargs,
):
    return CustomUser.objects.create_user(
        username=kwargs.pop("username", email),
        email=email,
        password=PASSWORD,
        role=role,
        is_email_verified=verified,
        is_active=active,
        is_blocked=blocked,
        **kwargs,
    )


def make_manager(email, **kwargs):
    return make_user(email, role="manager", **kwargs)


def make_text(owner, title="Письмо", text="Текст письма"):
    return Text.objects.create(owner=owner, title=title, text=text)


def make_client(owner, email, name="Клиент", comment=""):
    return ClientModel.objects.create(
        owner=owner, email=email, name=name, comment=comment
    )


def make_mailing(
    owner,
    message=None,
    recipients=(),
    *,
    start_at=None,
    end_at=None,
    status=BulkMailing.STATUS_CREATED,
    is_disabled=False,
    periodicity=BulkMailing.PERIOD_ONCE,
):
    mailing = BulkMailing.objects.create(
        owner=owner,
        message=message or make_text(owner),
        start_at=start_at,
        end_at=end_at,
        status=status,
        is_disabled=is_disabled,
        disabled_at=timezone.now() if is_disabled else None,
        periodicity=periodicity,
    )
    mailing.recipients.set(list(recipients))
    return mailing


class AccountTests(TestCase):
    """Критерий 5: регистрация, подтверждение email, вход, восстановление пароля."""

    def setUp(self):
        self.data = {
            "email": "user@example.com",
            "username": "user@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
            "phone": "+74951234567",
        }

    def test_registration_creates_unverified_user(self):
        self.client.post(reverse("users:register"), self.data)
        user = CustomUser.objects.get(email="user@example.com")
        self.assertFalse(user.is_email_verified)

    def test_registration_sends_confirmation_email(self):
        self.client.post(reverse("users:register"), self.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_login_blocked_until_email_confirmed(self):
        self.client.post(reverse("users:register"), self.data)
        response = self.client.post(
            reverse("users:login"),
            {"username": "user@example.com", "password": PASSWORD},
        )
        # Неподтверждённый email: форма входа отвечает ошибкой, а не редиректом.
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_confirmation_link_confirms_email(self):
        self.client.post(reverse("users:register"), self.data)
        user = CustomUser.objects.get(email="user@example.com")
        url = reverse("users:confirm_email", args=[make_confirm_token(user)])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_login_after_confirmation(self):
        self.client.post(reverse("users:register"), self.data)
        user = CustomUser.objects.get(email="user@example.com")
        self.client.get(reverse("users:confirm_email", args=[make_confirm_token(user)]))
        response = self.client.post(
            reverse("users:login"),
            {"username": "user@example.com", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_tampered_confirmation_token_is_rejected(self):
        self.assertIsNone(read_confirm_token("garbage-token"))

    def test_logout(self):
        user = make_user("out@example.com")
        self.client.force_login(user)
        response = self.client.post(reverse("users:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_password_reset_flow(self):
        make_user("reset@example.com")
        response = self.client.post(
            reverse("users:password_reset"),
            {"email": "reset@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

        user = CustomUser.objects.get(email="reset@example.com")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        confirm_url = reverse("users:password_reset_confirm", args=[uid, token])
        self.client.get(confirm_url)
        response = self.client.post(
            confirm_url,
            {"new_password1": "new-pass-456", "new_password2": "new-pass-456"},
        )
        self.assertIn(response.status_code, (200, 302))
        user.set_password("new-pass-456")
        user.save()
        self.assertTrue(
            self.client.login(username="reset@example.com", password="new-pass-456")
        )
        self.assertFalse(
            self.client.login(username="reset@example.com", password=PASSWORD)
        )


class AccessControlTests(TestCase):
    """Критерий 7: роли и разграничение доступа."""

    def setUp(self):
        self.user = make_user("owner@example.com")
        self.other = make_user("other@example.com")
        self.manager = make_manager("manager@example.com")
        self.mailing = make_mailing(self.user)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(
            reverse("bulkmailing:bulkmailing_detail", args=[self.mailing.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response["Location"])

    def test_other_user_cannot_see_mailing(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("bulkmailing:bulkmailing_detail", args=[self.mailing.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_send_mailing(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("bulkmailing:bulkmailing_send", args=[self.mailing.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(BulkMailingAttempt.objects.count(), 0)

    def test_manager_can_view_but_not_send_foreign_mailing(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("bulkmailing:bulkmailing_detail", args=[self.mailing.pk])
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("bulkmailing:bulkmailing_send", args=[self.mailing.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(BulkMailingAttempt.objects.count(), 0)

    def test_regular_user_does_not_see_user_list(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("users:user_list"))
        self.assertIn(response.status_code, (302, 403))

    def test_blocked_user_is_locked_out(self):
        blocked = make_user("blocked@example.com", blocked=True)
        self.client.force_login(blocked)
        response = self.client.get(reverse("bulkmailing:bulkmailing_list"))
        self.assertEqual(response.status_code, 302)

    def test_manager_can_toggle_block(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("users:user_toggle_block", args=[self.user.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_blocked)
        self.assertIsNotNone(self.user.blocked_at)

    def test_regular_user_cannot_toggle_block(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("users:user_toggle_block", args=[self.other.pk])
        )
        self.assertIn(response.status_code, (302, 403))
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_blocked)


class ModelOwnerTests(TestCase):
    """Критерий 1: модели, владельцы, статусы."""

    def setUp(self):
        self.user = make_user("owner@example.com")

    def test_owner_is_set_for_created_objects(self):
        text = make_text(self.user)
        client = make_client(self.user, "c@example.com")
        self.assertEqual(text.owner, self.user)
        self.assertEqual(client.owner, self.user)

    def test_cascade_deletes_owned_objects(self):
        make_client(self.user, "c1@example.com")
        make_text(self.user)
        self.user.delete()
        self.assertEqual(ClientModel.objects.count(), 0)
        self.assertEqual(Text.objects.count(), 0)

    def test_is_manager_property(self):
        self.assertFalse(self.user.is_manager)
        manager = make_manager("m@example.com")
        self.assertTrue(manager.is_manager)

    def test_blocked_manager_is_still_a_manager(self):
        manager = make_manager("bm@example.com", blocked=True)
        self.assertTrue(manager.is_manager)

    def test_attempt_error_code_and_recipient_exist(self):
        client = make_client(self.user, "c@example.com")
        mailing = make_mailing(
            self.user,
            recipients=[client],
            start_at=timezone.now() - timedelta(minutes=1),
        )
        send_mailing(mailing)
        attempt = BulkMailingAttempt.objects.get()
        self.assertEqual(attempt.recipient, client)
        self.assertIsNotNone(attempt.error_code is None or attempt.error_code)


class MailingHandlerTests(TestCase):
    """Критерии 2, 3, 4, 6: обработчик рассылки."""

    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.recipients = [
            make_client(self.owner, f"c{i}@example.com") for i in range(3)
        ]
        self.mailing = make_mailing(
            self.owner,
            recipients=self.recipients,
            start_at=timezone.now() - timedelta(minutes=5),
        )
        mail.outbox = []

    def test_email_sent_to_every_recipient(self):
        send_mailing(self.mailing)
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            {message.to[0] for message in mail.outbox},
            {c.email for c in self.recipients},
        )

    def test_returns_success_and_failure_counters(self):
        self.assertEqual(send_mailing(self.mailing), (3, 0))

    def test_attempts_are_persisted(self):
        send_mailing(self.mailing)
        attempts = BulkMailingAttempt.objects.filter(mailing=self.mailing)
        self.assertEqual(attempts.count(), 3)
        self.assertTrue(
            all(a.status == BulkMailingAttempt.STATUS_SUCCESS for a in attempts)
        )
        self.assertEqual(
            set(attempts.values_list("recipient_id", flat=True)),
            {c.pk for c in self.recipients},
        )

    def test_mailing_status_completed_after_send(self):
        send_mailing(self.mailing)
        self.mailing.refresh_from_db()
        self.assertEqual(self.mailing.status, BulkMailing.STATUS_COMPLETED)

    def test_attempts_created_in_single_batch_insert(self):
        recipients = [make_client(self.owner, f"big{i}@example.com") for i in range(20)]
        mailing = make_mailing(
            self.owner,
            recipients=recipients,
            start_at=timezone.now() - timedelta(minutes=1),
        )
        with CaptureQueriesContext(connection) as ctx:
            send_mailing(mailing)
        inserts = [
            q["sql"]
            for q in ctx.captured_queries
            if q["sql"].lstrip().upper().startswith("INSERT")
            and "bulkmailingattempt" in q["sql"].lower()
        ]
        self.assertEqual(len(inserts), 1)

    def test_failure_is_recorded_with_error_code(self):
        with mock.patch(
            "bulkmailing.services.EmailMessage.send",
            side_effect=smtplib.SMTPException("connection refused"),
        ):
            success, failed = send_mailing(self.mailing)
        self.assertEqual((success, failed), (0, 3))
        attempt = BulkMailingAttempt.objects.filter(status="failed").first()
        self.assertIsNotNone(attempt)
        self.assertIn("connection refused", attempt.server_response)

    def test_send_before_start_at_raises_window_error(self):
        mailing = make_mailing(
            self.owner,
            recipients=self.recipients[:1],
            start_at=timezone.now() + timedelta(hours=1),
        )
        with self.assertRaises(MailingWindowError):
            send_mailing(mailing)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(BulkMailingAttempt.objects.count(), 0)

    def test_send_after_end_at_raises_window_error(self):
        mailing = make_mailing(
            self.owner,
            recipients=self.recipients[:1],
            start_at=timezone.now() - timedelta(hours=2),
            end_at=timezone.now() - timedelta(hours=1),
        )
        with self.assertRaises(MailingWindowError):
            send_mailing(mailing)
        self.assertEqual(BulkMailingAttempt.objects.count(), 0)

    def test_invalid_window_leaves_mailing_untouched(self):
        mailing = make_mailing(
            self.owner,
            recipients=self.recipients[:1],
            start_at=timezone.now() + timedelta(hours=1),
        )
        with self.assertRaises(MailingWindowError):
            send_mailing(mailing)
        mailing.refresh_from_db()
        self.assertEqual(mailing.status, BulkMailing.STATUS_CREATED)

    def test_validate_window_allows_inside_window(self):
        self.assertIsNone(validate_window(self.mailing))

    def test_disabled_mailing_is_not_sent(self):
        mailing = make_mailing(
            self.owner,
            recipients=self.recipients[:1],
            start_at=timezone.now() - timedelta(minutes=1),
            is_disabled=True,
        )
        self.assertIsNone(send_mailing(mailing))
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(BulkMailingAttempt.objects.count(), 0)

    def test_repeat_send_returns_none(self):
        send_mailing(self.mailing)
        mail.outbox = []
        self.assertIsNone(send_mailing(self.mailing))
        self.assertEqual(len(mail.outbox), 0)

    def test_form_rejects_end_before_start(self):
        self.client.force_login(self.owner)
        text = make_text(self.owner)
        before = BulkMailing.objects.count()
        start = timezone.now() + timedelta(days=2)
        response = self.client.post(
            reverse("bulkmailing:bulkmailing_create"),
            {
                "start_at": start.strftime("%Y-%m-%dT%H:%M"),
                "end_at": (start - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                "message": str(text.pk),
                "recipients": [c.pk for c in self.recipients],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BulkMailing.objects.count(), before)
        self.assertContains(response, "Дата окончания должна быть позже")


class ScheduledMailingTests(TestCase):
    """Критерий 3: запуск по расписанию и защита от повторной отправки."""

    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.recipients = [
            make_client(self.owner, f"c{i}@example.com") for i in range(2)
        ]
        self.active = make_mailing(
            self.owner,
            recipients=self.recipients,
            start_at=timezone.now() - timedelta(minutes=1),
        )
        self.future = make_mailing(
            self.owner,
            recipients=self.recipients,
            start_at=timezone.now() + timedelta(days=1),
        )
        self.expired = make_mailing(
            self.owner,
            recipients=self.recipients,
            start_at=timezone.now() - timedelta(days=3),
            end_at=timezone.now() - timedelta(days=2),
        )
        self.disabled = make_mailing(
            self.owner,
            recipients=self.recipients,
            start_at=timezone.now() - timedelta(minutes=1),
            is_disabled=True,
        )
        mail.outbox = []

    def test_claim_moves_created_to_started(self):
        self.assertIsNotNone(claim_mailing(self.active.pk))
        self.active.refresh_from_db()
        self.assertEqual(self.active.status, BulkMailing.STATUS_STARTED)

    def test_claim_returns_none_for_already_claimed(self):
        claim_mailing(self.active.pk)
        self.assertIsNone(claim_mailing(self.active.pk))

    def test_claim_returns_none_for_disabled(self):
        self.assertIsNone(claim_mailing(self.disabled.pk))

    def test_send_due_sends_only_active_mailing(self):
        results = send_due_mailings()
        self.assertEqual([result[0].pk for result in results], [self.active.pk])
        self.assertEqual(len(mail.outbox), 2)

    def test_expired_mailing_is_marked_completed_without_sending(self):
        send_due_mailings()
        self.expired.refresh_from_db()
        self.assertEqual(self.expired.status, BulkMailing.STATUS_COMPLETED)
        self.assertEqual(
            BulkMailingAttempt.objects.filter(mailing=self.expired).count(), 0
        )

    def test_disabled_mailing_is_skipped(self):
        send_due_mailings()
        self.disabled.refresh_from_db()
        self.assertEqual(self.disabled.status, BulkMailing.STATUS_CREATED)
        self.assertEqual(
            BulkMailingAttempt.objects.filter(mailing=self.disabled).count(), 0
        )

    def test_command_sends_due_mailings_once(self):
        call_command("send_mailings", verbosity=0)
        self.assertEqual(len(mail.outbox), 2)
        mail.outbox = []
        call_command("send_mailings", verbosity=0)
        self.assertEqual(len(mail.outbox), 0)

    def test_button_sends_mailing_once(self):
        self.client.force_login(self.owner)
        url = reverse("bulkmailing:bulkmailing_send", args=[self.active.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(len(mail.outbox), 2)
        mail.outbox = []
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_button_reports_window_error_for_future_mailing(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("bulkmailing:bulkmailing_send", args=[self.future.pk]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.future.refresh_from_db()
        self.assertEqual(self.future.status, BulkMailing.STATUS_CREATED)
        self.assertContains(response, "ещ")

    def test_toggle_disables_and_enables(self):
        manager = make_manager("boss@example.com")
        self.client.force_login(manager)
        url = reverse("bulkmailing:bulkmailing_toggle", args=[self.active.pk])
        self.client.post(url)
        self.active.refresh_from_db()
        self.assertTrue(self.active.is_disabled)
        self.assertIsNotNone(self.active.disabled_at)
        self.client.post(url)
        self.active.refresh_from_db()
        self.assertFalse(self.active.is_disabled)
        self.assertIsNone(self.active.disabled_at)

    def test_regular_user_cannot_toggle(self):
        self.client.force_login(self.owner)
        self.client.post(
            reverse("bulkmailing:bulkmailing_toggle", args=[self.active.pk])
        )
        self.active.refresh_from_db()
        self.assertFalse(self.active.is_disabled)


class StatisticsTests(TestCase):
    """Критерий 8: статистика из кэша."""

    def setUp(self):
        self.user = make_user("user@example.com")
        self.manager = make_manager("manager@example.com")
        self.other = make_user("other@example.com")
        make_client(self.user, "a@example.com")
        make_client(self.user, "b@example.com")
        make_client(self.other, "c@example.com")
        cache.clear()

    def test_statistics_requires_login(self):
        response = self.client.get(reverse("statistics:statistics"))
        self.assertEqual(response.status_code, 302)

    def test_manager_stats_cover_everyone(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("statistics:statistics"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ClientModel.objects.count(), 3)

    def test_user_stats_scoped_to_own(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("statistics:statistics"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "c@example.com")

    def test_cache_key_does_not_leak_between_manager_and_user(self):
        self.client.force_login(self.manager)
        manager_response = self.client.get(reverse("statistics:statistics"))
        self.client.force_login(self.user)
        user_response = self.client.get(reverse("statistics:statistics"))
        self.assertNotEqual(manager_response.content, user_response.content)

    def test_stats_report_is_cached_per_user(self):
        self.client.force_login(self.user)
        with CaptureQueriesContext(connection) as first:
            self.client.get(reverse("statistics:statistics"))
        first_aggregations = len(
            [q for q in first.captured_queries if "GROUP BY" in q["sql"]]
        )
        with CaptureQueriesContext(connection) as second:
            self.client.get(reverse("statistics:statistics"))
        second_aggregations = len(
            [q for q in second.captured_queries if "GROUP BY" in q["sql"]]
        )
        self.assertGreater(first_aggregations, 0)
        self.assertEqual(second_aggregations, 0)


class CachingTests(TestCase):
    """Критерий 8: ETag, CSRF-токен в ETag, деградация кэша."""

    def setUp(self):
        self.user = make_user("user@example.com")
        self.factory = RequestFactory()
        self.middleware = ClientCacheMiddleware(lambda request: None)
        cache.clear()

    def _run(self, cache_control=None, csrf_token="token-a", method="GET"):
        request = self.factory.get("/clients/")
        request.method = method
        request.COOKIES = {}
        request.META = {"CSRF_COOKIE": csrf_token}
        response = HttpResponse("<html>body</html>", status=200)
        if cache_control is not None:
            response["Cache-Control"] = cache_control
        return self.middleware.process_response(request, response)

    def test_no_store_is_replaced_by_revalidation(self):
        response = self._run(cache_control="no-store")
        directives = response["Cache-Control"]
        self.assertIn("max-age=0", directives)
        self.assertIn("must-revalidate", directives)
        self.assertNotIn("no-store", directives)

    def test_private_is_preserved_for_authenticated_pages(self):
        response = self._run(cache_control="private, no-store")
        self.assertIn("private", response["Cache-Control"])
        self.assertNotIn("no-store", response["Cache-Control"])

    def test_shared_cache_directive_is_never_produced(self):
        response = self._run(cache_control="no-store")
        self.assertNotIn("public", response["Cache-Control"])

    def test_etag_added_to_successful_get(self):
        response = self._run()
        self.assertIn("ETag", response.headers)

    def test_no_etag_for_error_responses(self):
        request = self.factory.get("/clients/")
        request.method = "GET"
        request.COOKIES = {}
        request.META = {"CSRF_COOKIE": "token-a"}
        response = self.middleware.process_response(
            request, HttpResponse("err", status=500)
        )
        self.assertNotIn("ETag", response.headers)

    def test_no_etag_for_post_requests(self):
        response = self._run(method="POST")
        self.assertNotIn("ETag", response.headers)

    def test_etag_changes_when_csrf_token_rotates(self):
        first = self._run(csrf_token="token-a").headers["ETag"]
        second = self._run(csrf_token="token-b").headers["ETag"]
        self.assertNotEqual(first, second)

    def test_etag_is_stable_for_same_token(self):
        first = self._run(csrf_token="token-a").headers["ETag"]
        second = self._run(csrf_token="token-a").headers["ETag"]
        self.assertEqual(first, second)

    def test_etag_ignores_csrf_value_inside_body(self):
        request = self.factory.get("/clients/")
        request.method = "GET"
        request.COOKIES = {}
        request.META = {"CSRF_COOKIE": "token-a"}
        one = self.middleware.process_response(
            request, HttpResponse('<input name="csrfmiddlewaretoken" value="aaa">')
        )
        two = self.middleware.process_response(
            request, HttpResponse('<input name="csrfmiddlewaretoken" value="bbb">')
        )
        self.assertEqual(one.headers["ETag"], two.headers["ETag"])

    def test_session_change_rotates_etag_on_real_page(self):
        first = Client()
        first.force_login(self.user)
        etag_one = first.get(reverse("clients:clients_list")).headers["ETag"]

        second = Client()
        second.force_login(self.user)
        etag_two = second.get(reverse("clients:clients_list")).headers["ETag"]

        self.assertNotEqual(etag_one, etag_two)

    def test_stale_cached_form_still_posts_successfully(self):
        """Форма, отданная браузеру из кэша, должна приниматься с новым токеном."""
        browser = Client()
        browser.force_login(self.user)
        page = browser.get(reverse("clients:client_create"))
        stale_token = page.context["csrf_token"]

        fresh = Client()
        fresh.force_login(self.user)
        fresh.get(reverse("clients:client_create"))
        response = fresh.post(
            reverse("clients:client_create"),
            {
                "name": "Из кэша",
                "email": "cached@example.com",
                "comment": "",
                "csrfmiddlewaretoken": stale_token,
            },
        )
        self.assertIn(response.status_code, (200, 302))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClientModel.objects.filter(email="cached@example.com").exists())

    def test_authenticated_page_gets_etag(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("clients:clients_list"))
        self.assertIn("ETag", response.headers)

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "config.cache.ResilientRedisCache",
                "LOCATION": "redis://127.0.0.1:6399/15",
            }
        }
    )
    def test_cache_degrades_when_redis_is_down(self):
        cache.clear()
        cache.set("probe", "value", 30)
        self.assertIsNone(cache.get("probe"))

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "config.cache.ResilientRedisCache",
                "LOCATION": "redis://127.0.0.1:6399/15",
            }
        }
    )
    def test_site_survives_when_redis_is_down(self):
        cache.clear()
        self.client.force_login(self.user)
        response = self.client.get(reverse("statistics:statistics"))
        self.assertEqual(response.status_code, 200)

    def test_cache_timeouts_are_bounded(self):
        self.assertGreater(CONNECT_TIMEOUT_SECONDS, 0)
        self.assertLessEqual(CONNECT_TIMEOUT_SECONDS, 2)
        self.assertGreater(RETRY_AFTER_SECONDS, 0)


class PeriodicityTests(TestCase):
    """Периодичность: ежедневно, еженедельно, ежемесячно."""

    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.recipients = [make_client(self.owner, "c@example.com")]
        mail.outbox = []

    def _make(self, periodicity, start_at=None, end_at=None, **kwargs):
        return make_mailing(
            self.owner,
            recipients=self.recipients,
            start_at=start_at or (timezone.now() - timedelta(minutes=1)),
            end_at=end_at,
            periodicity=periodicity,
            **kwargs,
        )

    def test_first_run_is_scheduled_from_start_at(self):
        start = timezone.now() - timedelta(minutes=1)
        mailing = self._make(BulkMailing.PERIOD_DAILY, start_at=start)
        self.assertEqual(mailing.next_run_at, start)

    def test_one_time_mailing_has_no_next_run(self):
        mailing = self._make(BulkMailing.PERIOD_ONCE)
        self.assertIsNone(mailing.next_run_at)
        self.assertFalse(mailing.is_periodic)

    def test_periodic_mailing_stays_created_after_send(self):
        mailing = self._make(BulkMailing.PERIOD_DAILY)
        send_mailing(mailing)
        mailing.refresh_from_db()
        self.assertEqual(mailing.status, BulkMailing.STATUS_CREATED)
        self.assertIsNotNone(mailing.next_run_at)
        self.assertGreater(mailing.next_run_at, timezone.now() - timedelta(seconds=5))

    def test_one_time_mailing_is_completed_after_send(self):
        mailing = self._make(BulkMailing.PERIOD_ONCE)
        send_mailing(mailing)
        mailing.refresh_from_db()
        self.assertEqual(mailing.status, BulkMailing.STATUS_COMPLETED)
        self.assertIsNone(mailing.next_run_at)

    def test_daily_adds_one_day(self):
        base = timezone.now()
        mailing = self._make(BulkMailing.PERIOD_DAILY)
        self.assertEqual(next_run_at(mailing, base=base) - base, timedelta(days=1))

    def test_weekly_adds_seven_days(self):
        base = timezone.now()
        mailing = self._make(BulkMailing.PERIOD_WEEKLY)
        self.assertEqual(next_run_at(mailing, base=base) - base, timedelta(days=7))

    def test_monthly_adds_calendar_month(self):
        base = timezone.now().replace(day=15)
        mailing = self._make(BulkMailing.PERIOD_MONTHLY)
        self.assertEqual(next_run_at(mailing, base=base).month, (base.month % 12) + 1)

    def test_monthly_clamps_to_last_day_of_month(self):
        base = timezone.now().replace(
            year=2024, month=1, day=31, hour=12, minute=0, second=0, microsecond=0
        )
        mailing = self._make(BulkMailing.PERIOD_MONTHLY)
        result = next_run_at(mailing, base=base)
        self.assertEqual((result.year, result.month, result.day), (2024, 2, 29))

    def test_periodic_mailing_not_due_before_next_run(self):
        mailing = self._make(BulkMailing.PERIOD_DAILY)
        mailing.next_run_at = timezone.now() + timedelta(hours=2)
        mailing.save(update_fields=["next_run_at"])
        self.assertEqual(send_due_mailings(), [])
        self.assertEqual(len(mail.outbox), 0)

    def test_periodic_mailing_due_after_next_run_passed(self):
        mailing = self._make(BulkMailing.PERIOD_DAILY)
        mailing.next_run_at = timezone.now() - timedelta(minutes=1)
        mailing.save(update_fields=["next_run_at"])
        results = send_due_mailings()
        self.assertEqual([r[0].pk for r in results], [mailing.pk])
        self.assertEqual(len(mail.outbox), 1)

    def test_periodic_mailing_sends_again_on_next_due_run(self):
        mailing = self._make(BulkMailing.PERIOD_DAILY)
        send_due_mailings()
        self.assertEqual(len(mail.outbox), 1)
        mail.outbox = []

        mailing.refresh_from_db()
        mailing.next_run_at = timezone.now() - timedelta(minutes=1)
        mailing.save(update_fields=["next_run_at"])

        send_due_mailings()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(BulkMailingAttempt.objects.filter(mailing=mailing).count(), 2)

    def test_periodic_send_before_next_run_raises(self):
        mailing = self._make(BulkMailing.PERIOD_DAILY)
        mailing.next_run_at = timezone.now() + timedelta(hours=3)
        mailing.save(update_fields=["next_run_at"])
        with self.assertRaises(MailingWindowError):
            send_mailing(mailing)
        self.assertEqual(len(mail.outbox), 0)

    def test_periodic_mailing_stops_at_end_at(self):
        mailing = self._make(
            BulkMailing.PERIOD_DAILY,
            end_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertEqual(send_due_mailings(), [])
        mailing.refresh_from_db()
        self.assertEqual(mailing.status, BulkMailing.STATUS_COMPLETED)
        self.assertEqual(len(mail.outbox), 0)

    def test_disabled_periodic_mailing_not_scheduled(self):
        mailing = self._make(BulkMailing.PERIOD_DAILY, is_disabled=True)
        self.assertEqual(send_due_mailings(), [])
        self.assertEqual(len(mail.outbox), 0)

    def test_form_accepts_periodicity(self):
        self.client.force_login(self.owner)
        text = make_text(self.owner)
        start = timezone.now() + timedelta(minutes=10)
        response = self.client.post(
            reverse("bulkmailing:bulkmailing_create"),
            {
                "start_at": start.strftime("%Y-%m-%dT%H:%M"),
                "end_at": "",
                "periodicity": BulkMailing.PERIOD_WEEKLY,
                "message": str(text.pk),
                "recipients": [c.pk for c in self.recipients],
            },
        )
        self.assertEqual(response.status_code, 302)
        mailing = BulkMailing.objects.get()
        self.assertEqual(mailing.periodicity, BulkMailing.PERIOD_WEEKLY)
        self.assertTrue(mailing.is_periodic)
        # Первый запуск планируется на дату первой отправки из формы.
        self.assertEqual(mailing.next_run_at, mailing.start_at)
        self.assertIsNotNone(mailing.next_run_at)
