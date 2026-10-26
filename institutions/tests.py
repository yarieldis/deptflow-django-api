from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from institutions.models import Institution


class InstitutionTests(TestCase):
    def test_create_institution(self):
        inst = Institution.objects.create(name="Acme", code="ACME Inc")
        self.assertEqual(inst.code, "acme-inc")
        self.assertTrue(inst.is_active)

    def test_duplicate_code_rejected(self):
        Institution.objects.create(name="Acme", code="acme")
        with self.assertRaises(IntegrityError):
            Institution.objects.create(name="Other", code="ACME")

    def test_parent_hierarchy(self):
        parent = Institution.objects.create(name="Parent", code="parent")
        child = Institution.objects.create(name="Child", code="child", parent=parent)
        self.assertEqual(child.parent, parent)

    def test_cycle_detection_rejected(self):
        a = Institution.objects.create(name="A", code="a")
        b = Institution.objects.create(name="B", code="b", parent=a)
        a.parent = b
        with self.assertRaises(ValidationError):
            a.save()

    def test_self_parent_rejected(self):
        a = Institution.objects.create(name="A", code="a")
        a.parent = a
        with self.assertRaises(ValidationError):
            a.save()
