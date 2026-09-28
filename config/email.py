import smtplib

from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend


class RecordingSMTPBackend(SMTPEmailBackend):
    """SMTP-бэкенд, который запоминает ответ почтового сервера.

    Django по умолчанию сообщает только число отправленных писем, поэтому
    «ответ сервера» в истории попыток приходилось писать константой. Здесь
    после отправки выполняется NOOP, и реальная строка ответа сервера
    (например ``250 2.0.0 Ok: queued as 3F2A1B``) попадает в
    ``last_response``.

    При локальном бэкенде (locmem/console) ``last_response`` остаётся None —
    там реального SMTP-сервера нет.
    """

    last_response = None
    last_code = None

    def _send(self, email_message):
        result = super()._send(email_message)
        self.last_response = None
        self.last_code = None
        connection = getattr(self, "connection", None)
        if connection is None:
            return result
        try:
            code, message = connection.noop()
        except (smtplib.SMTPException, OSError):
            return result
        self.last_code = code
        self.last_response = (
            message.decode("utf-8", "replace")
            if isinstance(message, bytes)
            else message
        )
        return result
