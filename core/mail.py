from django.core.mail.backends.base import BaseEmailBackend

from core.email_utils import email_to_dict
from core.tasks import send_emails_task


class CeleryEmailBackend(BaseEmailBackend):
    """Django 6 ``MAILERS``-aware backend that dispatches email through Celery.

    Configure via ``MAILERS["default"]`` with an ``OPTIONS`` entry naming the
    mailer that performs the actual delivery, e.g.::

        MAILERS = {
            "default": {
                "BACKEND": "core.mail.CeleryEmailBackend",
                "OPTIONS": {"delivery_mailer": "smtp"},
            },
            "smtp": {"BACKEND": "django.core.mail.backends.smtp.EmailBackend"},
        }
    """

    def __init__(self, *args, delivery_mailer="default", **kwargs):
        self.delivery_mailer = delivery_mailer
        super().__init__(*args, **kwargs)

    def send_messages(self, email_messages):
        payload = [email_to_dict(message) for message in email_messages]
        return [send_emails_task.delay(payload, self.delivery_mailer)]
