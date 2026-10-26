import json

from django.test import Client, TestCase

from core.testing import auth_headers
from institutions.models import Department, Institution


class InstitutionEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.auth = auth_headers()

    def _headers(self, tenant_id=None):
        headers = dict(self.auth)
        if tenant_id is not None:
            headers["HTTP_X_INSTITUTION_ID"] = str(tenant_id)
        return headers

    def _post_institution(self, name, code):
        return self.client.post(
            "/api/institutions",
            data=json.dumps({"name": name, "code": code}),
            content_type="application/json",
            **self.auth,
        )

    def test_create_institution(self):
        resp = self._post_institution("Acme", "ACME Inc")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["code"], "acme-inc")
        self.assertEqual(data["name"], "Acme")

    def test_duplicate_institution_code_conflict(self):
        self._post_institution("Acme", "acme")
        resp = self._post_institution("Other", "ACME")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["code"], "conflict")

    def test_list_institutions_requires_tenant(self):
        resp = self.client.get("/api/institutions", **self.auth)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "tenant_required")

    def test_list_institutions_returns_current_tenant(self):
        inst_id = self._post_institution("Acme", "acme").json()["id"]
        resp = self.client.get("/api/institutions", **self._headers(inst_id))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()[0]["name"], "Acme")

    def test_requires_authentication(self):
        resp = self.client.get("/api/institutions")
        self.assertEqual(resp.status_code, 401)


class DepartmentEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.auth = auth_headers()
        self.inst = Institution.objects.create(name="Acme", code="acme")

    def _headers(self, tenant=None):
        headers = dict(self.auth)
        if tenant is not None:
            headers["HTTP_X_INSTITUTION_ID"] = str(tenant)
        return headers

    def _post_department(self, name, code, tenant=None):
        return self.client.post(
            "/api/departments",
            data=json.dumps({"name": name, "code": code}),
            content_type="application/json",
            **self._headers(tenant),
        )

    def test_create_department_stamps_tenant_from_header(self):
        resp = self._post_department("Eng", "ENG", self.inst.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["code"], "eng")
        dept = Department.objects.get(code="eng")
        self.assertEqual(dept.institution, self.inst)

    def test_create_department_requires_tenant(self):
        resp = self._post_department("Eng", "eng")
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_department_code_conflict(self):
        self._post_department("Eng", "eng", self.inst.pk)
        resp = self._post_department("Eng2", "ENG", self.inst.pk)
        self.assertEqual(resp.status_code, 409)

    def test_list_departments_is_tenant_scoped(self):
        other = Institution.objects.create(name="Other", code="other")
        Department.objects.create(institution=self.inst, name="A", code="a")
        Department.objects.create(institution=other, name="B", code="b")

        resp = self.client.get("/api/departments", **self._headers(self.inst.pk))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([d["name"] for d in resp.json()], ["A"])
