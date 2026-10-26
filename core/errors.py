class DomainError(Exception):
    """Base for business-layer errors, mapped to HTTP by a Ninja handler."""

    status_code = 400
    code = "domain_error"

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ForbiddenError(DomainError):
    status_code = 403
    code = "forbidden"


class TenantRequiredError(DomainError):
    status_code = 400
    code = "tenant_required"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class InvalidStateError(DomainError):
    status_code = 409
    code = "invalid_state"
