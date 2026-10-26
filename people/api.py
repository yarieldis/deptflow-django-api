import uuid

from ninja import Router

from people import services
from people.schemas import (
    MembershipIn,
    MembershipOut,
    PersonIn,
    PersonOut,
    PersonUpdate,
    RoleOut,
)

router = Router()


@router.post("/people", response=PersonOut)
def create_person(request, payload: PersonIn):
    return services.create_person(**payload.model_dump())


@router.put("/people/{person_id}", response=PersonOut)
def update_person(request, person_id: uuid.UUID, payload: PersonUpdate):
    return services.update_person(
        person_id=person_id, **payload.model_dump(exclude_none=True)
    )


@router.get("/people", response=list[PersonOut])
def list_people(request):
    return services.list_people()


@router.get("/people/{person_id}/memberships", response=list[MembershipOut])
def list_person_memberships(request, person_id: uuid.UUID):
    return services.list_person_memberships(person_id=person_id)


@router.post("/memberships", response=MembershipOut)
def assign_membership(request, payload: MembershipIn):
    return services.assign_membership(**payload.model_dump())


@router.get("/roles", response=list[RoleOut])
def list_roles(request):
    return services.list_roles()
