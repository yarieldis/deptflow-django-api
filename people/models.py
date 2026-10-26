from django.conf import settings
from django.db import models

from core.models import TenantModel


class Role(TenantModel):
    """Configurable per-institution organizational role.

    Distinct from Django's auth groups/permissions: these describe what a person
    *does* in a department. ``can_approve_documents`` / ``can_publish_documents``
    gate the document workflow.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    can_approve_documents = models.BooleanField(default=False)
    can_publish_documents = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="uniq_role_name_per_institution",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Person(TenantModel):
    """Organizational record, optionally linked to a login account.

    A person need not have a login (``user`` is nullable). A login may map to
    one person per institution.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="persons",
    )
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    job_title = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
