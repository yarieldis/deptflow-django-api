from ninja import Router

from institutions import services
from institutions.schemas import (
    DepartmentIn,
    DepartmentOut,
    InstitutionIn,
    InstitutionOut,
)

router = Router()


@router.post("/institutions", response=InstitutionOut)
def create_institution(request, payload: InstitutionIn):
    return services.create_institution(name=payload.name, code=payload.code)


@router.get("/institutions", response=list[InstitutionOut])
def list_institutions(request):
    return services.list_institutions()


@router.post("/departments", response=DepartmentOut)
def create_department(request, payload: DepartmentIn):
    return services.create_department(name=payload.name, code=payload.code)


@router.get("/departments", response=list[DepartmentOut])
def list_departments(request):
    return services.list_departments()
