from django.core.exceptions import ValidationError
from django.db import models

from core.models import TenantModel, UUIDModel
from core.utils import normalize_code


class Institution(UUIDModel):
    """Top-level organization — the multi-tenant boundary.

    Institutions may form an optional parent/child umbrella hierarchy. The
    institution's ``id`` is the tenant id used to scope all tenant-owned data.
    """

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.code = normalize_code(self.code)
        if self.parent_id is not None and self.would_create_cycle(self.parent):
            raise ValidationError("Institution hierarchy cannot contain cycles.")
        super().save(*args, **kwargs)

    def would_create_cycle(self, new_parent) -> bool:
        """Return True if assigning ``new_parent`` would make this institution
        its own ancestor."""
        if new_parent is None:
            return False
        seen = set()
        node = new_parent
        while node is not None:
            if node.pk in seen:
                return True  # defensive: pre-existing cycle in the graph
            seen.add(node.pk)
            if self.pk is not None and node.pk == self.pk:
                return True
            node = node.parent
        return False


class Department(TenantModel):
    """Department owned by an institution; optional nesting and head person."""

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
    parent_department = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    head_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="uniq_department_code_per_institution",
            )
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.code = normalize_code(self.code)
        if self.parent_department_id is not None:
            parent = self.parent_department
            if parent.institution_id != self.institution_id:
                raise ValidationError(
                    "Department parent must belong to the same institution."
                )
            if self.would_create_cycle(parent):
                raise ValidationError("Department hierarchy cannot contain cycles.")
        super().save(*args, **kwargs)

    def would_create_cycle(self, new_parent) -> bool:
        """Return True if assigning ``new_parent`` would make this department
        its own ancestor."""
        if new_parent is None:
            return False
        seen = set()
        node = new_parent
        while node is not None:
            if node.pk in seen:
                return True
            seen.add(node.pk)
            if self.pk is not None and node.pk == self.pk:
                return True
            node = node.parent_department
        return False
