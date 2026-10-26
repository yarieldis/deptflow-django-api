import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from core.testing import auth_headers
from institutions.models import Department, Institution
from people.models import Person, PersonDepartment, Role


class WorkflowTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.inst = Institution.objects.create(name="Acme", code="acme")
        self.dept = Department.objects.create(
            institution=self.inst, name="Eng", code="eng"
        )

        self.uploader_user, self.uploader = self._member("uploader", "Engineer")
        self.approver_user, self.approver = self._member(
            "approver", "Reviewer", can_approve=True
        )
        self.publisher_user, self.publisher = self._member(
            "publisher", "Publisher", can_publish=True
        )

        self.uploader_h = self._headers(self.uploader_user)
        self.approver_h = self._headers(self.approver_user)
        self.publisher_h = self._headers(self.publisher_user)

    def _member(self, username, role_name, can_approve=False, can_publish=False):
        user = get_user_model().objects.create_user(
            username=username, password="secret"
        )
        person = Person.objects.create(
            institution=self.inst,
            first_name=username.title(),
            last_name="Test",
            user=user,
        )
        role = Role.objects.create(
            institution=self.inst,
            name=role_name,
            can_approve_documents=can_approve,
            can_publish_documents=can_publish,
        )
        PersonDepartment.objects.create(
            person=person, department=self.dept, role=role, start_date=timezone.localdate()
        )
        return user, person

    def _headers(self, user):
        return {
            **auth_headers(user),
            "HTTP_X_INSTITUTION_ID": str(self.inst.pk),
        }

    def _create(self, headers, title="Spec"):
        file = SimpleUploadedFile("spec.txt", b"content", content_type="text/plain")
        return self.client.post(
            "/api/documents",
            data={
                "department_id": str(self.dept.pk),
                "title": title,
                "file": file,
            },
            **headers,
        )

    def _action(self, url, headers, payload=None):
        data = json.dumps(payload if payload is not None else {})
        return self.client.post(
            url, data=data, content_type="application/json", **headers
        )

    def _add_version(self, doc_id, headers):
        file = SimpleUploadedFile("spec2.txt", b"v2", content_type="text/plain")
        return self.client.post(
            f"/api/documents/{doc_id}/versions", data={"file": file}, **headers
        )

    def test_full_workflow(self):
        doc_id = self._create(self.uploader_h).json()["id"]

        r = self._action(f"/api/documents/{doc_id}/submit", self.uploader_h)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["status"], "pending_approval")

        r = self._action(
            f"/api/documents/{doc_id}/approve", self.approver_h, {"comment": "ok"}
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["status"], "approved")

        r = self._action(f"/api/documents/{doc_id}/publish", self.publisher_h)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["status"], "published")
        self.assertEqual(r.json()["major_version"], 1)
        self.assertEqual(r.json()["minor_version"], 0)

        r = self._action(
            f"/api/documents/{doc_id}/unpublish", self.publisher_h, {"reason": "fix"}
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["status"], "pending_approval")

        r = self._action(
            f"/api/documents/{doc_id}/reject",
            self.approver_h,
            {"comment": "needs work", "requires_new_upload": True},
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["status"], "draft")

        # Submit is blocked until a new upload clears the gate.
        r = self._action(f"/api/documents/{doc_id}/submit", self.uploader_h)
        self.assertEqual(r.status_code, 409)

        r = self._add_version(doc_id, self.uploader_h)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["version_number"], 2)

        r = self._action(f"/api/documents/{doc_id}/submit", self.uploader_h)
        self.assertEqual(r.status_code, 200, r.content)
        r = self._action(
            f"/api/documents/{doc_id}/approve", self.approver_h, {"comment": "ok"}
        )
        self.assertEqual(r.status_code, 200, r.content)
        r = self._action(f"/api/documents/{doc_id}/publish", self.publisher_h)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["status"], "published")
        self.assertEqual(r.json()["major_version"], 2)
        self.assertEqual(r.json()["minor_version"], 0)

    def test_self_approval_denied(self):
        doc_id = self._create(self.approver_h).json()["id"]
        self._action(f"/api/documents/{doc_id}/submit", self.approver_h)
        r = self._action(
            f"/api/documents/{doc_id}/approve", self.approver_h, {"comment": "ok"}
        )
        self.assertEqual(r.status_code, 403)

    def test_non_publisher_cannot_publish(self):
        doc_id = self._create(self.uploader_h).json()["id"]
        self._action(f"/api/documents/{doc_id}/submit", self.uploader_h)
        self._action(
            f"/api/documents/{doc_id}/approve", self.approver_h, {"comment": "ok"}
        )
        r = self._action(f"/api/documents/{doc_id}/publish", self.uploader_h)
        self.assertEqual(r.status_code, 403)

    def test_archive_requires_published(self):
        doc_id = self._create(self.uploader_h).json()["id"]
        r = self._action(f"/api/documents/{doc_id}/archive", self.uploader_h)
        self.assertEqual(r.status_code, 409)

    def test_unpublish_requires_reason(self):
        doc_id = self._create(self.uploader_h).json()["id"]
        self._action(f"/api/documents/{doc_id}/submit", self.uploader_h)
        self._action(
            f"/api/documents/{doc_id}/approve", self.approver_h, {"comment": "ok"}
        )
        self._action(f"/api/documents/{doc_id}/publish", self.publisher_h)
        r = self._action(
            f"/api/documents/{doc_id}/unpublish", self.publisher_h, {"reason": ""}
        )
        self.assertEqual(r.status_code, 409)
