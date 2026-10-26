import contextvars
import uuid
from contextlib import contextmanager

_current_tenant: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "current_tenant", default=None
)


def current_tenant_id() -> uuid.UUID | None:
    """Return the institution id scoping the current request/context."""
    return _current_tenant.get()


@contextmanager
def tenant_scope(tenant_id: uuid.UUID | None):
    """Context manager to set the current tenant for a block of code."""
    token = _current_tenant.set(tenant_id)
    try:
        yield
    finally:
        _current_tenant.reset(token)


class TenantMiddleware:
    """Resolve the current tenant from the ``X-Institution-Id`` header.

    The tenant is stored in a ``contextvars`` value so the service layer can
    read it without threading the request object through every call.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = None
        header = request.headers.get("X-Institution-Id")
        if header:
            try:
                tenant_id = uuid.UUID(header)
            except ValueError:
                tenant_id = None

        token = _current_tenant.set(tenant_id)
        try:
            return self.get_response(request)
        finally:
            _current_tenant.reset(token)
