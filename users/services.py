import logging

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse

logger = logging.getLogger(__name__)

CONFIRM_SALT = "users.email-confirm"
CONFIRM_MAX_AGE = 60 * 60 * 24


def make_confirm_token(user) -> str:
    return signing.dumps({"pk": user.pk}, salt=CONFIRM_SALT)


def read_confirm_token(token: str):
    from users.models import CustomUser

    try:
        data = signing.loads(token, salt=CONFIRM_SALT, max_age=CONFIRM_MAX_AGE)
    except signing.BadSignature:
        return None
    try:
        return CustomUser.objects.get(pk=data["pk"])
    except (CustomUser.DoesNotExist, KeyError, TypeError, ValueError):
        return None


def send_confirmation_email(user, absolute_url: str) -> bool:
    try:
        sent = send_mail(
            subject="Подтвердите email в PRMessenger",
            message=(
                "Здравствуйте!\n\n"
                "Подтвердите свой email, чтобы активировать аккаунт:\n"
                f"{absolute_url}\n\n"
                "Ссылка действует 24 часа.\n"
                "Если вы не регистрировались — просто проигнорируйте письмо."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Не удалось отправить письмо для подтверждения email")
        return False
    if sent == 0:
        logger.error("SMTP вернул 0 отправленных писем для %s", user.email)
        return False
    return True


def build_confirm_url(request, user) -> str:
    return request.build_absolute_uri(
        reverse("users:confirm_email", args=[make_confirm_token(user)])
    )
