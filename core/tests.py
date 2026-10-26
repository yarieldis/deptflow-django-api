import uuid

from django.apps import apps
from django.conf import settings
from django.test import RequestFactory, SimpleTestCase, TestCase

from core.models import TenantQuerySet, User
from core.tenancy import TenantMiddleware, current_tenant_id, tenant_scope


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


class TenancyTests(SimpleTestCase):
    def test_default_tenant_is_none(self):
        self.assertIsNone(current_tenant_id())

    def test_tenant_scope_sets_and_resets(self):
        tenant = uuid.uuid4()
        self.assertIsNone(current_tenant_id())
        with tenant_scope(tenant):
            self.assertEqual(current_tenant_id(), tenant)
        self.assertIsNone(current_tenant_id())

    def test_middleware_reads_header(self):
        tenant = uuid.uuid4()
        request = RequestFactory().get("/", headers={"X-Institution-Id": str(tenant)})
        seen = {}

        def get_response(req):
            seen["tenant"] = current_tenant_id()
            return None

        TenantMiddleware(get_response)(request)
        self.assertEqual(seen["tenant"], tenant)

    def test_middleware_resets_tenant_after_request(self):
        tenant = uuid.uuid4()
        request = RequestFactory().get("/", headers={"X-Institution-Id": str(tenant)})

        TenantMiddleware(lambda req: None)(request)
        self.assertIsNone(current_tenant_id())

    def test_middleware_ignores_invalid_header(self):
        request = RequestFactory().get("/", headers={"X-Institution-Id": "not-a-uuid"})
        seen = {}

        def get_response(req):
            seen["tenant"] = current_tenant_id()
            return None

        TenantMiddleware(get_response)(request)
        self.assertIsNone(seen["tenant"])


class TenantQuerySetTests(SimpleTestCase):
    def test_for_tenant_none_returns_empty(self):
        qs = TenantQuerySet(model=User)
        self.assertFalse(qs.for_tenant(None).exists())
