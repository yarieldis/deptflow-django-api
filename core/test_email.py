from django.core import mail
from django.test import SimpleTestCase, override_settings

TEST_MAILERS = {
    "default": {
        "BACKEND": "core.mail.CeleryEmailBackend",
        "OPTIONS": {"delivery_mailer": "console"},
    },
    "console": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
}


@override_settings(MAILERS=TEST_MAILERS)
class EmailTests(SimpleTestCase):
    def test_send_mail_dispatches_through_celery(self):
        mail.send_mail(
            "Subject", "Body", "from@example.com", ["to@example.com"]
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Subject")
