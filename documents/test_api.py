from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from core.testing import auth_headers
from documents.models import Document, DocumentVersion
from institutions.models import Department, Institution
from people.models import Person, PersonDepartment, Role


class DocumentsEndpointTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.inst = Institution.objects.create(name="Acme", code="acme")
        self.dept = Department.objects.create(
            institution=self.inst, name="Eng", code="eng"
        )
        self.user = get_user_model().objects.create_user(
            username="jane", password="secret"
        )
        self.person = Person.objects.create(
            institution=self.inst,
            first_name="Jane",
            last_name="Doe",
            user=self.user,
        )
        self.role = Role.objects.create(institution=self.inst, name="Engineer")
        PersonDepartment.objects.create(
            person=self.person,
            department=self.dept,
            role=self.role,
            start_date=timezone.localdate(),
        )
        self.headers = {
            **auth_headers(self.user),
            "HTTP_X_INSTITUTION_ID": str(self.inst.pk),
        }

    def _create_document(self, title="Spec", dept=None):
        file = SimpleUploadedFile("spec.txt", b"hello world", content_type="text/plain")
        return self.client.post(
            "/api/documents",
            data={
                "department_id": str(dept.pk if dept else self.dept.pk),
                "title": title,
                "file": file,
            },
            **self.headers,
        )

    def test_create_document_with_first_version(self):
        resp = self._create_document()
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["title"], "Spec")

        doc = Document.objects.get(id=data["id"])
        self.assertEqual(doc.versions.count(), 1)
        self.assertEqual(doc.versions.get().version_number, 1)
        self.assertTrue(doc.versions.get().storage_key)

    def test_list_documents_is_department_scoped(self):
        self._create_document("Spec")
        other_dept = Department.objects.create(
            institution=self.inst, name="Ops", code="ops"
        )
        Document.objects.create(
            institution=self.inst,
            department=other_dept,
            title="Hidden",
            created_by_person=self.person,
        )

        resp = self.client.get("/api/documents", **self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([d["title"] for d in resp.json()], ["Spec"])

    def test_get_document_with_versions(self):
        doc_id = self._create_document("Spec").json()["id"]
        resp = self.client.get(f"/api/documents/{doc_id}", **self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["versions"]), 1)
        self.assertEqual(resp.json()["versions"][0]["version_number"], 1)

    def test_add_version_gets_next_number(self):
        doc_id = self._create_document("Spec").json()["id"]
        file = SimpleUploadedFile("spec2.txt", b"v2", content_type="text/plain")
        resp = self.client.post(
            f"/api/documents/{doc_id}/versions",
            data={"file": file, "change_note": "revised"},
            **self.headers,
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["version_number"], 2)
        self.assertEqual(DocumentVersion.objects.filter(document_id=doc_id).count(), 2)

    def test_non_member_cannot_create(self):
        outsider_user = get_user_model().objects.create_user(
            username="outsider", password="secret"
        )
        Person.objects.create(
            institution=self.inst,
            first_name="Out",
            last_name="Sider",
            user=outsider_user,
        )
        headers = {
            **auth_headers(outsider_user),
            "HTTP_X_INSTITUTION_ID": str(self.inst.pk),
        }
        file = SimpleUploadedFile("spec.txt", b"x", content_type="text/plain")
        resp = self.client.post(
            "/api/documents",
            data={
                "department_id": str(self.dept.pk),
                "title": "Spec",
                "file": file,
            },
            **headers,
        )
        self.assertEqual(resp.status_code, 403)

    def test_add_version_requires_draft(self):
        doc_id = self._create_document("Spec").json()["id"]
        Document.objects.filter(id=doc_id).update(status=Document.Status.PUBLISHED)
        file = SimpleUploadedFile("spec2.txt", b"v2", content_type="text/plain")
        resp = self.client.post(
            f"/api/documents/{doc_id}/versions",
            data={"file": file},
            **self.headers,
        )
        self.assertEqual(resp.status_code, 409)
