import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from institutions.models import Department, Institution
from people.models import Person, PersonDepartment, Role


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


class MembershipTests(TestCase):
    def setUp(self):
        self.inst = Institution.objects.create(name="Acme", code="acme")
        self.dept = Department.objects.create(
            institution=self.inst, name="Eng", code="eng"
        )
        self.person = Person.objects.create(
            institution=self.inst, first_name="Jane", last_name="Doe"
        )
        self.role = Role.objects.create(institution=self.inst, name="Engineer")

    def test_assign_membership_is_active(self):
        m = PersonDepartment.objects.create(
            person=self.person,
            department=self.dept,
            role=self.role,
            start_date=timezone.localdate(),
        )
        self.assertTrue(m.is_active_on())

    def test_future_end_date_is_still_active(self):
        today = timezone.localdate()
        m = PersonDepartment.objects.create(
            person=self.person,
            department=self.dept,
            role=self.role,
            start_date=today - datetime.timedelta(days=1),
            end_date=today + datetime.timedelta(days=5),
        )
        self.assertTrue(m.is_active_on(today))

    def test_ended_membership_is_not_active(self):
        today = timezone.localdate()
        m = PersonDepartment.objects.create(
            person=self.person,
            department=self.dept,
            role=self.role,
            start_date=today - datetime.timedelta(days=10),
            end_date=today - datetime.timedelta(days=1),
        )
        self.assertFalse(m.is_active_on(today))

    def test_rejoin_creates_new_membership(self):
        today = timezone.localdate()
        PersonDepartment.objects.create(
            person=self.person,
            department=self.dept,
            role=self.role,
            start_date=today - datetime.timedelta(days=30),
            end_date=today - datetime.timedelta(days=10),
        )
        PersonDepartment.objects.create(
            person=self.person, department=self.dept, role=self.role, start_date=today
        )
        self.assertEqual(self.person.memberships.count(), 2)
