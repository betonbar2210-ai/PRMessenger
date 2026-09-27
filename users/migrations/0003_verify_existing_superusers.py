from django.db import migrations


def mark_existing_superusers_verified(apps, schema_editor):
    """Суперпользователи созданы через createsuperuser, а не через регистрацию,
    поэтому им не нужно подтверждение email."""
    User = apps.get_model("users", "CustomUser")
    User.objects.filter(is_superuser=True).update(
        is_email_verified=True, is_active=True
    )


def unverify(apps, schema_editor):
    User = apps.get_model("users", "CustomUser")
    User.objects.filter(is_superuser=True).update(is_email_verified=True)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_customuser_role_and_verification"),
    ]

    operations = [
        migrations.RunPython(mark_existing_superusers_verified, unverify),
    ]
