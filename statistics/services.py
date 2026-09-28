from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from bulkmailing.models import BulkMailing, BulkMailingAttempt


def attempts_qs(user):
    qs = BulkMailingAttempt.objects.all()
    if not user.is_manager:
        qs = qs.filter(mailing__owner=user)
    return qs


def mailings_qs(user):
    qs = BulkMailing.objects.all()
    if not user.is_manager:
        qs = qs.filter(owner=user)
    return qs


def collect(user) -> dict:
    attempts = attempts_qs(user)
    mailings = mailings_qs(user)

    totals = attempts.aggregate(
        success=Count("pk", filter=Q(status=BulkMailingAttempt.STATUS_SUCCESS)),
        failed=Count("pk", filter=Q(status=BulkMailingAttempt.STATUS_FAILED)),
    )
    success = totals["success"] or 0
    failed = totals["failed"] or 0
    total = success + failed

    status_labels = dict(BulkMailing.STATUS_CHOICES)
    by_status = mailings.values("status").annotate(count=Count("pk")).order_by("status")

    return {
        "success_attempts": success,
        "failed_attempts": failed,
        "total_attempts": total,
        "sent_messages": success,
        "success_rate": round(success * 100 / total, 1) if total else 0.0,
        "total_mailings": mailings.count(),
        "active_mailings": mailings.filter(status=BulkMailing.STATUS_STARTED).count(),
        "completed_mailings": mailings.filter(
            status=BulkMailing.STATUS_COMPLETED
        ).count(),
        "disabled_mailings": mailings.filter(is_disabled=True).count(),
        "mailings_by_status": [
            {
                "label": status_labels.get(row["status"], row["status"]),
                "count": row["count"],
            }
            for row in by_status
        ],
        "daily": daily_breakdown(user),
        "top_mailings": top_mailings(user),
    }


def daily_breakdown(user, days: int = 14) -> list:
    since = timezone.now() - timedelta(days=days)
    rows = (
        attempts_qs(user)
        .filter(attempted_at__gte=since)
        .annotate(day=TruncDate("attempted_at"))
        .values("day")
        .annotate(
            success=Count("pk", filter=Q(status=BulkMailingAttempt.STATUS_SUCCESS)),
            failed=Count("pk", filter=Q(status=BulkMailingAttempt.STATUS_FAILED)),
        )
        .order_by("day")
    )
    return [
        {
            "day": row["day"],
            "success": row["success"],
            "failed": row["failed"],
            "total": row["success"] + row["failed"],
        }
        for row in rows
    ]


def top_mailings(user, limit: int = 10) -> list:
    rows = (
        attempts_qs(user)
        .values("mailing_id", "mailing__message__title")
        .annotate(
            success=Count("pk", filter=Q(status=BulkMailingAttempt.STATUS_SUCCESS)),
            failed=Count("pk", filter=Q(status=BulkMailingAttempt.STATUS_FAILED)),
        )
        .order_by("-success", "-failed")[:limit]
    )
    return [
        {
            "mailing_id": row["mailing_id"],
            "title": row["mailing__message__title"],
            "success": row["success"],
            "failed": row["failed"],
            "total": row["success"] + row["failed"],
        }
        for row in rows
    ]
