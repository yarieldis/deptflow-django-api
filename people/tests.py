from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from institutions.models import Institution
from people.models import Person, Role


class RoleTests(TestCase):
    def setUp(self):
        self.inst = Institution.objects.create(name="Acme", code="acme")

    def test_unique_name_per_institution(self):
        Role.objects.create(institution=self.inst, name="Reviewer")
        with self.assertRaises(IntegrityError):
            Role.objects.create(institution=self.inst, name="Reviewer")

    def test_same_name_across_institutions(self):
        other = Institution.objects.create(name="Other", code="other")
        Role.objects.create(institution=self.inst, name="Reviewer")
        Role.objects.create(institution=other, name="Reviewer")  # allowed
        self.assertEqual(Role.objects.count(), 2)

    def test_permission_flags_default_false(self):
        role = Role.objects.create(institution=self.inst, name="Reviewer")
        self.assertFalse(role.can_approve_documents)
        self.assertFalse(role.can_publish_documents)


class PersonTests(TestCase):
    def setUp(self):
        self.inst = Institution.objects.create(name="Acme", code="acme")

    def test_person_without_login(self):
        person = Person.objects.create(
            institution=self.inst, first_name="Jane", last_name="Doe"
        )
        self.assertIsNone(person.user)

    def test_person_linked_to_login(self):
        user = get_user_model().objects.create_user(username="jane", password="secret")
        person = Person.objects.create(
            institution=self.inst, first_name="Jane", last_name="Doe", user=user
        )
        self.assertEqual(person.user, user)


class TenantScopingTests(TestCase):
    def test_for_tenant_filters_by_institution(self):
        inst_a = Institution.objects.create(name="A", code="a")
        inst_b = Institution.objects.create(name="B", code="b")
        Role.objects.create(institution=inst_a, name="RoleA")
        Role.objects.create(institution=inst_b, name="RoleB")

        self.assertEqual(Role.objects.for_tenant(inst_a.pk).count(), 1)
        self.assertEqual(Role.objects.for_tenant(inst_a.pk).get().name, "RoleA")
        self.assertEqual(Role.objects.for_tenant(inst_b.pk).get().name, "RoleB")
