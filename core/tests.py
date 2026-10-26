import uuid

from django.apps import apps
from django.conf import settings
from django.test import TestCase

from core.models import User


class BootstrapTests(TestCase):
    def test_auth_user_model_is_custom(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "core.User")

    def test_apps_are_installed(self):
        installed = {app for app in apps.app_configs}
        for expected in ("core", "institutions", "people", "documents"):
            self.assertIn(expected, installed)

    def test_user_has_uuid_primary_key(self):
        user = User.objects.create_user(username="alice", password="secret")
        self.assertIsInstance(user.pk, uuid.UUID)
