from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_owner(apps, model_name):
    """Проставляет владельца для существующих записей.

    Берётся первый суперпользователь, иначе — первый пользователь.
    Раньше разграничения не было, поэтому все прежние записи
    достанутся первому администратору.
    """
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Model = apps.get_model("clients", model_name)

    if not Model.objects.filter(owner__isnull=True).exists():
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


def unassign_owner(apps, model_name):
    Model = apps.get_model("clients", model_name)
    Model.objects.update(owner=None)


class Migration(migrations.Migration):
    dependencies = [
        ("clients", "0002_alter_client_options_alter_client_comment_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="owner",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="clients",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Владелец",
            ),
        ),
        migrations.RunPython(
            lambda apps, schema_editor: assign_owner(apps, "Client"),
            lambda apps, schema_editor: unassign_owner(apps, "Client"),
        ),
        migrations.AlterField(
            model_name="client",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="clients",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Владелец",
            ),
        ),
    ]
