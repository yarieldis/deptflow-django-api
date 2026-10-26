from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from institutions.models import Department, Institution
from people.models import Person


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


class DepartmentTests(TestCase):
    def setUp(self):
        self.inst = Institution.objects.create(name="Acme", code="acme")

    def test_create_department_normalizes_code(self):
        dept = Department.objects.create(
            institution=self.inst, name="Engineering", code="ENG"
        )
        self.assertEqual(dept.code, "eng")
        self.assertEqual(dept.institution, self.inst)

    def test_unique_code_per_institution(self):
        Department.objects.create(institution=self.inst, name="Eng", code="eng")
        with self.assertRaises(IntegrityError):
            Department.objects.create(institution=self.inst, name="Eng2", code="ENG")

    def test_same_code_across_institutions(self):
        other = Institution.objects.create(name="Other", code="other")
        Department.objects.create(institution=self.inst, name="Eng", code="eng")
        Department.objects.create(institution=other, name="Eng", code="eng")  # allowed
        self.assertEqual(Department.objects.count(), 2)

    def test_cross_institution_parent_rejected(self):
        other = Institution.objects.create(name="Other", code="other")
        parent = Department.objects.create(
            institution=other, name="Parent", code="parent"
        )
        with self.assertRaises(ValidationError):
            Department.objects.create(
                institution=self.inst,
                name="Child",
                code="child",
                parent_department=parent,
            )

    def test_nesting_cycle_rejected(self):
        a = Department.objects.create(institution=self.inst, name="A", code="a")
        b = Department.objects.create(
            institution=self.inst, name="B", code="b", parent_department=a
        )
        a.parent_department = b
        with self.assertRaises(ValidationError):
            a.save()

    def test_head_person(self):
        person = Person.objects.create(
            institution=self.inst, first_name="Jane", last_name="Doe"
        )
        dept = Department.objects.create(
            institution=self.inst, name="Eng", code="eng", head_person=person
        )
        self.assertEqual(dept.head_person, person)

    def test_for_tenant_scopes_departments(self):
        other = Institution.objects.create(name="Other", code="other")
        Department.objects.create(institution=self.inst, name="A", code="a")
        Department.objects.create(institution=other, name="B", code="b")
        self.assertEqual(Department.objects.for_tenant(self.inst.pk).count(), 1)
