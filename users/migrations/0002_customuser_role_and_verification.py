from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="is_email_verified",
            field=models.BooleanField(default=False, verbose_name="Email подтверждён"),
        ),
        migrations.AddField(
            model_name="customuser",
            name="is_blocked",
            field=models.BooleanField(default=False, verbose_name="Заблокирован"),
        ),
        migrations.AddField(
            model_name="customuser",
            name="blocked_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Дата и время блокировки"
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="role",
            field=models.CharField(
                choices=[("user", "Пользователь"), ("manager", "Менеджер")],
                default="user",
                max_length=10,
                verbose_name="Роль",
            ),
        ),
    ]
