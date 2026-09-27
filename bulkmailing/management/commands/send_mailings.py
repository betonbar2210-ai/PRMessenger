import sys
import time

from django.core.management.base import BaseCommand

from bulkmailing.services import send_due_mailings


class Command(BaseCommand):
    help = "Отправляет рассылки по расписанию (однократно или в режиме --watch)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="постоянный режим: проверять рассылки каждые --interval секунд",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="интервал проверки в секундах (по умолчанию 60)",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        if options["watch"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Watcher запущен: проверка каждые {interval} сек "
                    f"(Ctrl+C для остановки)"
                )
            )
            try:
                while True:
                    self.run_once()
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\nОстановлено"))
                sys.exit(0)
        else:
            self.run_once()

    def run_once(self):
        try:
            results = send_due_mailings()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Ошибка отправки рассылок: {exc}"))
            return

        if not results:
            self.stdout.write(self.style.WARNING("Нет рассылок для отправки"))
            return

        for mailing, success_count, failed_count in results:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{mailing}] отправлено: {success_count}, ошибок: {failed_count}"
                )
            )
