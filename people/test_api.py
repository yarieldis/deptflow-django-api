import json

from django.test import Client, TestCase

from core.testing import auth_headers
from institutions.models import Department, Institution
from people.models import Person, PersonDepartment, Role


class PeopleEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.auth = auth_headers()
        self.inst = Institution.objects.create(name="Acme", code="acme")

    def _headers(self):
        return {**self.auth, "HTTP_X_INSTITUTION_ID": str(self.inst.pk)}

    def test_create_and_list_people(self):
        resp = self.client.post(
            "/api/people",
            data=json.dumps({"first_name": "Jane", "last_name": "Doe"}),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["first_name"], "Jane")

        resp = self.client.get("/api/people", **self._headers())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_create_person_requires_tenant(self):
        resp = self.client.post(
            "/api/people",
            data=json.dumps({"first_name": "Jane", "last_name": "Doe"}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_person(self):
        person = Person.objects.create(
            institution=self.inst, first_name="Jane", last_name="Doe"
        )
        resp = self.client.put(
            f"/api/people/{person.pk}",
            data=json.dumps({"job_title": "Engineer"}),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["job_title"], "Engineer")

    def test_list_roles_is_tenant_scoped(self):
        other = Institution.objects.create(name="Other", code="other")
        Role.objects.create(institution=self.inst, name="A")
        Role.objects.create(institution=other, name="B")
        resp = self.client.get("/api/roles", **self._headers())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([r["name"] for r in resp.json()], ["A"])


class MembershipEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.auth = auth_headers()
        self.inst = Institution.objects.create(name="Acme", code="acme")
        self.dept = Department.objects.create(
            institution=self.inst, name="Eng", code="eng"
        )
        self.person = Person.objects.create(
            institution=self.inst, first_name="Jane", last_name="Doe"
        )
        self.role = Role.objects.create(institution=self.inst, name="Engineer")

    def _headers(self):
        return {**self.auth, "HTTP_X_INSTITUTION_ID": str(self.inst.pk)}

    def test_assign_membership(self):
        resp = self.client.post(
            "/api/memberships",
            data=json.dumps(
                {
                    "person_id": str(self.person.pk),
                    "department_id": str(self.dept.pk),
                    "role_id": str(self.role.pk),
                    "start_date": "2024-01-01",
                }
            ),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PersonDepartment.objects.count(), 1)

    def test_assign_membership_cross_tenant_rejected(self):
        other = Institution.objects.create(name="Other", code="other")
        other_dept = Department.objects.create(institution=other, name="X", code="x")
        resp = self.client.post(
            "/api/memberships",
            data=json.dumps(
                {
                    "person_id": str(self.person.pk),
                    "department_id": str(other_dept.pk),
                    "role_id": str(self.role.pk),
                    "start_date": "2024-01-01",
                }
            ),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(resp.status_code, 404)

    def test_list_memberships(self):
        PersonDepartment.objects.create(
            person=self.person,
            department=self.dept,
            role=self.role,
            start_date="2024-01-01",
        )
        resp = self.client.get(f"/api/people/{self.person.pk}/memberships", **self._headers())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
