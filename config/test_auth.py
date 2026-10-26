import json

from django.test import Client, TestCase

from core.testing import auth_headers


class AuthEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()

    def _register(self, username="jane", email="jane@example.com"):
        return self.client.post(
            "/auth/registration/",
            data=json.dumps(
                {
                    "username": username,
                    "email": email,
                    "password1": "Str0ngPass!",
                    "password2": "Str0ngPass!",
                }
            ),
            content_type="application/json",
        )

    def test_register_login_refresh(self):
        reg = self._register()
        self.assertEqual(reg.status_code, 201)
        self.assertIn("access", reg.json())
        self.assertIn("refresh", reg.json())

        login = self.client.post(
            "/auth/login/",
            data=json.dumps({"username": "jane", "password": "Str0ngPass!"}),
            content_type="application/json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.json())

        refresh = self.client.post(
            "/auth/token/refresh/",
            data=json.dumps({"refresh": login.json()["refresh"]}),
            content_type="application/json",
        )
        self.assertEqual(refresh.status_code, 200)
        self.assertIn("access", refresh.json())

    def test_user_details_requires_token(self):
        resp = self.client.get("/auth/user/")
        self.assertEqual(resp.status_code, 401)

    def test_ninja_endpoint_requires_jwt(self):
        resp = self.client.get("/api/institutions")
        self.assertEqual(resp.status_code, 401)

    def test_ninja_endpoint_accepts_jwt(self):
        headers = auth_headers()
        resp = self.client.get("/api/institutions", **headers)
        # Authenticated but no tenant header → tenant_required, proving auth passed.
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "tenant_required")
