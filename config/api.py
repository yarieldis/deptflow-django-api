from ninja import NinjaAPI

from core.errors import DomainError
from institutions.api import router as institutions_router

api = NinjaAPI(title="DeptFlow API")


@api.exception_handler(DomainError)
def domain_error_handler(request, exc: DomainError):
    return api.create_response(
        request,
        {"detail": exc.message or str(exc), "code": exc.code},
        status=exc.status_code,
    )


api.add_router("/", institutions_router)
