from django.contrib.auth.models import AbstractUser
from django.db import models

from core.uuid import uuid7


class UUIDModel(models.Model):
    """Abstract base providing a time-ordered UUIDv7 primary key."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True


class User(AbstractUser):
    """Custom auth user with a UUID primary key.

    DeptFlow separates the organizational record (``people.Person``) from the
    login account. This model is the login account; ``Person.user`` links to it
    via a nullable FK.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    def __str__(self) -> str:
        return self.username


class TenantQuerySet(models.QuerySet):
    """QuerySet with explicit tenant scoping.

    ``objects`` stays unscoped by default (normal Django semantics); callers
    scope explicitly with ``.for_tenant(tenant_id)``. The service layer is the
    only place that queries tenant-owned models and always scopes.
    """

    def for_tenant(self, tenant_id):
        if tenant_id is None:
            return self.none()
        return self.filter(institution_id=tenant_id)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    pass


class TenantModel(UUIDModel):
    """Abstract base for tenant-owned entities (carries ``institution_id``)."""

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.RESTRICT,
        related_name="+",
        editable=False,
    )

    objects = TenantManager()

    class Meta:
        abstract = True
