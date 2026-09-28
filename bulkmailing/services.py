import calendar
import smtplib
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import BulkMailing, BulkMailingAttempt


class MailingWindowError(ValidationError):
    """Обработчик вызван вне разрешённого интервала рассылки.

    Отдельный тип, чтобы вызывающий код отличал «не время отправлять» от
    ошибок валидации полей формы.
    """


def validate_window(mailing: BulkMailing, *, now=None) -> None:
    """Проверяет, что сейчас разрешено отправлять эту рассылку.

    Если время вызова обработчика не попадает в интервал рассылки, возникает
    ``MailingWindowError`` — отправка не выполняется и вызывающий получает
    явную ошибку вместо молчаливого выхода.
    """
    now = now or timezone.now()
    if mailing.is_periodic:
        # У периодической рассылки «пора» определяется очередным запуском,
        # а не только первой датой.
        earliest = mailing.next_run_at or mailing.start_at
        if earliest and now < earliest:
            raise MailingWindowError(
                "Рассылка ещё не может быть отправлена: следующий запуск "
                f"{earliest:%d.%m.%Y %H:%M} наступит позже."
            )
    elif mailing.start_at and now < mailing.start_at:
        raise MailingWindowError(
            "Рассылка ещё не может быть отправлена: начало "
            f"{mailing.start_at:%d.%m.%Y %H:%M} наступит позже."
        )
    if mailing.end_at and now > mailing.end_at:
        raise MailingWindowError(
            "Срок отправки рассылки истёк: окно закрыто "
            f"{mailing.end_at:%d.%m.%Y %H:%M}."
        )


def _add_month(value):
    """Прибавляет один календарный месяц, обрезая день по длине месяца."""
    month = value.month + 1
    year = value.year
    if month > 12:
        month = 1
        year += 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def next_run_at(mailing: BulkMailing, base=None):
    """Следующий запуск периодической рассылки или ``None`` для однократной."""
    if not mailing.is_periodic:
        return None
    base = base or timezone.now()
    if mailing.periodicity == BulkMailing.PERIOD_DAILY:
        return base + timedelta(days=1)
    if mailing.periodicity == BulkMailing.PERIOD_WEEKLY:
        return base + timedelta(days=7)
    return _add_month(base)


def update_statuses() -> int:
    return BulkMailing.objects.filter(
        status__in=[BulkMailing.STATUS_CREATED, BulkMailing.STATUS_STARTED],
        end_at__lt=timezone.now(),
    ).update(status=BulkMailing.STATUS_COMPLETED)


def get_due_mailings():
    now = timezone.now()
    update_statuses()
    active = BulkMailing.objects.filter(
        status=BulkMailing.STATUS_CREATED,
        is_disabled=False,
    ).exclude(end_at__lt=now)

    # Однократные ждут первого запуска, периодические — следующего run_at.
    once = active.filter(
        periodicity=BulkMailing.PERIOD_ONCE,
    ).filter(Q(start_at__isnull=True) | Q(start_at__lte=now))

    periodic = active.filter(
        periodicity__in=BulkMailing.PERIODIC_VALUES,
    ).filter(Q(next_run_at__isnull=True) | Q(next_run_at__lte=now))

    return once | periodic


def claim_mailing(mailing_pk: int):
    with transaction.atomic():
        claimed = (
            BulkMailing.objects.select_for_update()
            .filter(
                pk=mailing_pk,
                status=BulkMailing.STATUS_CREATED,
                is_disabled=False,
            )
            .first()
        )
        if claimed is None:
            return None
        claimed.status = BulkMailing.STATUS_STARTED
        claimed.save(update_fields=["status"])
    return claimed


def send_due_mailings() -> list[tuple[BulkMailing, int, int]]:
    results = []
    for mailing in list(get_due_mailings()):
        outcome = send_mailing(mailing)
        if outcome is None:
            # Рассылку уже забрал другой процесс — второй раз не отправляем.
            continue
        success_count, failed_count = outcome
        results.append((mailing, success_count, failed_count))
    return results


def send_mailing(mailing: BulkMailing) -> tuple[int, int] | None:
    """Отправляет рассылку, если её ещё никто не забрал.

    Возвращает ``(успешно, ошибок)``. ``None`` означает, что отправка не
    состоялась: рассылку уже обрабатывает другой процесс либо её отключил
    менеджер. Если обработчик вызван вне интервала рассылки, возникает
    ``MailingWindowError``.
    """
    # Сначала время вызова, потом захват: рассылку вне окна нельзя даже
    # забрать, иначе она «застрянет» в статусе «Запущена» без отправки.
    validate_window(mailing)

    claimed = claim_mailing(mailing.pk)
    if claimed is None:
        return None
    mailing = claimed

    recipients = mailing.recipients.all().distinct()
    success_count = 0
    failed_count = 0
    attempts = []

    for client in recipients:
        attempt = BulkMailingAttempt(
            mailing=mailing,
            recipient=client,
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
            smtp_code = getattr(exc, "smtp_code", None)
            attempt.error_code = str(smtp_code) if smtp_code else None
            failed_count += 1
        else:
            attempt.status = BulkMailingAttempt.STATUS_SUCCESS
            # Бэкенд запоминает реальный ответ SMTP-сервера; у локальных
            # бэкендов (locmem/console) сервера нет, поэтому пишем факт приёма.
            response = getattr(
                getattr(email, "connection", None), "last_response", None
            )
            attempt.server_response = response or f"Письмо принято ({client.email})"
            success_count += 1
        attempts.append(attempt)

    # Попытки сохраняются одним пакетным запросом вместо INSERT на получателя.
    BulkMailingAttempt.objects.bulk_create(attempts)

    if mailing.is_periodic:
        # Периодическая рассылка возвращается в «Создана» и ждёт следующего
        # запуска, поэтому попадёт в выборку планировщика снова.
        mailing.next_run_at = next_run_at(mailing)
        mailing.status = BulkMailing.STATUS_CREATED
    else:
        mailing.next_run_at = None
        mailing.status = BulkMailing.STATUS_COMPLETED
    mailing.save(update_fields=["status", "next_run_at"])

    return success_count, failed_count
