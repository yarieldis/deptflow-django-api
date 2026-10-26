from django.db.models import Q
from django.utils import timezone

from people.models import PersonDepartment


class DocumentAccessPolicy:
    """Department-scoped access decisions for the document workflow.

    Access is derived from active membership in the document's owning
    department; approval/publish additionally require a role permission flag.
    """

    @staticmethod
    def active_department_ids(person) -> set:
        today = timezone.localdate()
        memberships = PersonDepartment.objects.filter(
            person=person, start_date__lte=today
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
        return set(memberships.values_list("department_id", flat=True))

    @classmethod
    def _active_membership(cls, person, department):
        today = timezone.localdate()
        return (
            PersonDepartment.objects.filter(
                person=person, department=department, start_date__lte=today
            )
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            .first()
        )

    def can_access(self, person, department) -> bool:
        return self._active_membership(person, department) is not None

    def can_submit(self, person, document) -> bool:
        return self._active_membership(person, document.department) is not None

    def can_review(self, person, document) -> bool:
        membership = self._active_membership(person, document.department)
        return membership is not None and membership.role.can_approve_documents

    def can_approve(self, person, document) -> bool:
        if not self.can_review(person, document):
            return False
        latest = document.latest_version
        return latest is None or latest.created_by_person_id != person.pk

    def can_publish(self, person, document) -> bool:
        membership = self._active_membership(person, document.department)
        return membership is not None and membership.role.can_publish_documents

    def can_unpublish(self, person, document) -> bool:
        return self.can_publish(person, document)

    def can_archive(self, person, document) -> bool:
        return self._active_membership(person, document.department) is not None
