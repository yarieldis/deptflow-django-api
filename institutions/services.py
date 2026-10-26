from django.db import IntegrityError

from core.errors import ConflictError, NotFoundError, TenantRequiredError
from core.tenancy import current_tenant_id
from institutions.models import Department, Institution


def require_tenant():
    """Return the current tenant id or raise if no tenant is in scope."""
    tenant_id = current_tenant_id()
    if tenant_id is None:
        raise TenantRequiredError("X-Institution-Id header is required.")
    return tenant_id


def create_institution(*, name: str, code: str) -> Institution:
    """Create a new institution (which becomes a new tenant)."""
    try:
        return Institution.objects.create(name=name, code=code)
    except IntegrityError as exc:
        raise ConflictError("Institution code already exists.") from exc


def list_institutions() -> list[Institution]:
    """Return the current tenant's institution."""
    tenant_id = require_tenant()
    institution = Institution.objects.filter(id=tenant_id).first()
    if institution is None:
        raise NotFoundError("Institution not found.")
    return [institution]


def create_department(*, name: str, code: str) -> Department:
    """Create a department stamped with the current tenant."""
    tenant_id = require_tenant()
    if not Institution.objects.filter(id=tenant_id).exists():
        raise NotFoundError("Institution not found.")
    try:
        return Department.objects.create(
            institution_id=tenant_id, name=name, code=code
        )
    except IntegrityError as exc:
        raise ConflictError(
            "Department code already exists in this institution."
        ) from exc


def list_departments() -> list[Department]:
    """List departments in the current tenant."""
    tenant_id = require_tenant()
    return list(Department.objects.for_tenant(tenant_id))
