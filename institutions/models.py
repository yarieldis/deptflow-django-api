from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from core.models import UUIDModel


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

    @staticmethod
    def normalize_code(value: str) -> str:
        return slugify(value or "")

    def save(self, *args, **kwargs):
        self.code = self.normalize_code(self.code)
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
