from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_owner(apps, schema_editor):
    """Проставляет владельца для существующих записей."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Model = apps.get_model("texts", "Text")

    pending = Model.objects.filter(owner__isnull=True)
    if not pending.exists():
        return None

    owner = (
        User.objects.filter(is_superuser=True).order_by("pk").first()
        or User.objects.order_by("pk").first()
    )
    if owner is None:
        raise RuntimeError(
            "Нельзя определить владельца существующих записей: "
            "в базе нет ни одного пользователя."
        )
    return Model.objects.filter(owner__isnull=True).update(owner=owner)


def unassign_owner(apps, schema_editor):
    Text = apps.get_model("texts", "Text")
    Text.objects.update(owner=None)


class Migration(migrations.Migration):
    dependencies = [
        ("texts", "0002_alter_text_options_alter_text_text_alter_text_title"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="text",
            name="owner",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="texts",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Владелец",
            ),
        ),
        migrations.RunPython(assign_owner, unassign_owner),
        migrations.AlterField(
            model_name="text",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="texts",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Владелец",
            ),
        ),
    ]
