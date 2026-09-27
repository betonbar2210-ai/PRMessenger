from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_owner(apps, schema_editor):
    """Проставляет владельца для существующих рассылок."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    BulkMailing = apps.get_model("bulkmailing", "BulkMailing")

    if not BulkMailing.objects.filter(owner__isnull=True).exists():
        return None

    owner = (
        User.objects.filter(is_superuser=True).order_by("pk").first()
        or User.objects.order_by("pk").first()
    )
    if owner is None:
        raise RuntimeError(
            "Нельзя определить владельца существующих рассылок: "
            "в базе нет ни одного пользователя."
        )
    return BulkMailing.objects.filter(owner__isnull=True).update(owner=owner)


def unassign_owner(apps, schema_editor):
    BulkMailing = apps.get_model("bulkmailing", "BulkMailing")
    BulkMailing.objects.update(owner=None)


class Migration(migrations.Migration):
    dependencies = [
        ("bulkmailing", "0002_alter_bulkmailing_options_and_more"),
        ("clients", "0003_client_owner"),
        ("texts", "0003_text_owner"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="bulkmailing",
            name="owner",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="mailings",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Владелец",
            ),
        ),
        migrations.AddField(
            model_name="bulkmailing",
            name="is_disabled",
            field=models.BooleanField(
                default=False, verbose_name="Отключена менеджером"
            ),
        ),
        migrations.AddField(
            model_name="bulkmailing",
            name="disabled_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Дата и время отключения"
            ),
        ),
        migrations.RunPython(assign_owner, unassign_owner),
        migrations.AlterField(
            model_name="bulkmailing",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="mailings",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Владелец",
            ),
        ),
        migrations.AddIndex(
            model_name="bulkmailing",
            index=models.Index(
                fields=["owner", "status"], name="bulkmailing_owner_i_7f67ae_idx"
            ),
        ),
    ]
