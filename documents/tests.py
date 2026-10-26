from django.db import IntegrityError
from django.test import TestCase

from documents.models import Document, DocumentType, DocumentVersion
from institutions.models import Department, Institution
from people.models import Person


class DocumentModelTests(TestCase):
    def setUp(self):
        self.inst = Institution.objects.create(name="Acme", code="acme")
        self.dept = Department.objects.create(
            institution=self.inst, name="Eng", code="eng"
        )
        self.person = Person.objects.create(
            institution=self.inst, first_name="Jane", last_name="Doe"
        )

    def _doc(self, **kwargs):
        return Document.objects.create(
            institution=self.inst,
            department=self.dept,
            title="Spec",
            created_by_person=self.person,
            **kwargs,
        )

    def _version(self, doc, number=1, key="k1", **kwargs):
        return DocumentVersion.objects.create(
            document=doc,
            version_number=number,
            storage_key=key,
            file_name="a.txt",
            content_type="text/plain",
            size_bytes=10,
            created_by_person=self.person,
            **kwargs,
        )

    def test_document_defaults(self):
        doc = self._doc()
        self.assertEqual(doc.status, Document.Status.DRAFT)
        self.assertEqual(doc.major_version, 0)
        self.assertEqual(doc.minor_version, 0)
        self.assertEqual(doc.version, "0.0")

    def test_version_numbering_and_latest(self):
        doc = self._doc()
        v1 = self._version(doc, 1, "k1")
        v2 = self._version(doc, 2, "k2")
        self.assertEqual(doc.versions.count(), 2)
        self.assertEqual(doc.latest_version, v2)
        self.assertEqual(doc.next_version_number(), 3)

    def test_first_version_number_is_one(self):
        doc = self._doc()
        self.assertEqual(doc.next_version_number(), 1)

    def test_duplicate_version_number_rejected(self):
        doc = self._doc()
        self._version(doc, 1, "k1")
        with self.assertRaises(IntegrityError):
            self._version(doc, 1, "k2")

    def test_document_type_is_tenant_owned(self):
        dt = DocumentType.objects.create(institution=self.inst, name="Policy")
        self.assertEqual(dt.institution, self.inst)
