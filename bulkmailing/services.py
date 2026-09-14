import smtplib

from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Q
from django.utils import timezone

from .models import BulkMailing, BulkMailingAttempt


def update_statuses() -> int:
    """Помечает завершёнными рассылки, срок которых уже истёк.

    Возвращает количество обновлённых рассылок.
    """
    return BulkMailing.objects.filter(
        status__in=[BulkMailing.STATUS_CREATED, BulkMailing.STATUS_STARTED],
        end_at__lt=timezone.now(),
    ).update(status=BulkMailing.STATUS_COMPLETED)


def get_due_mailings():
    """Рассылки, готовые к отправке сейчас (статус «Создана», наступило start_at)."""
    now = timezone.now()
    update_statuses()
    return (
        BulkMailing.objects.filter(
            status=BulkMailing.STATUS_CREATED,
        )
        .filter(
            Q(start_at__isnull=True) | Q(start_at__lte=now),
        )
        .exclude(end_at__lt=now)
    )


def send_due_mailings():
    """Отправляет все подошедшие по времени рассылки.

    Возвращает список кортежей (рассылка, отправлено_успешно, ошибок).
    """
    results = []
    for mailing in get_due_mailings():
        success_count, failed_count = send_mailing(mailing)
        results.append((mailing, success_count, failed_count))
    return results


def send_mailing(mailing: BulkMailing) -> tuple[int, int]:
    if mailing.end_at and mailing.end_at <= timezone.now():
        mailing.status = BulkMailing.STATUS_COMPLETED
        mailing.save(update_fields=["status"])
        return 0, 0

    recipients = mailing.recipients.all().distinct()
    success_count = 0
    failed_count = 0

    for client in recipients:
        attempt = BulkMailingAttempt.objects.create(
            mailing=mailing,
            status=BulkMailingAttempt.STATUS_FAILED,
        )
        try:
            email = EmailMessage(
                subject=mailing.message.title,
                body=mailing.message.text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[client.email],
            )
            email.send(fail_silently=False)
        except (
            smtplib.SMTPException,
            ValueError,
            ConnectionError,
            TimeoutError,
            OSError,
        ) as exc:
            attempt.server_response = str(exc)
            attempt.save()
            failed_count += 1
        else:
            attempt.status = BulkMailingAttempt.STATUS_SUCCESS
            attempt.server_response = "Письмо успешно отправлено"
            attempt.save()
            success_count += 1

    if mailing.end_at and mailing.end_at <= timezone.now():
        mailing.status = BulkMailing.STATUS_COMPLETED
    else:
        mailing.status = BulkMailing.STATUS_STARTED
    mailing.save(update_fields=["status"])

    return success_count, failed_count
