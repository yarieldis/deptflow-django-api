from django.db import IntegrityError

from core.errors import ConflictError, NotFoundError
from core.tenancy import require_tenant
from institutions.models import Department
from people.models import Person, PersonDepartment, Role


def create_person(
    *, first_name: str, last_name: str, email: str = "", phone: str = "", job_title: str = ""
) -> Person:
    tenant_id = require_tenant()
    return Person.objects.create(
        institution_id=tenant_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        job_title=job_title,
    )


def update_person(*, person_id, **fields) -> Person:
    tenant_id = require_tenant()
    person = Person.objects.for_tenant(tenant_id).filter(id=person_id).first()
    if person is None:
        raise NotFoundError("Person not found.")
    for key, value in fields.items():
        setattr(person, key, value)
    person.save()
    return person


def list_people() -> list[Person]:
    tenant_id = require_tenant()
    return list(Person.objects.for_tenant(tenant_id))


def list_person_memberships(*, person_id) -> list[PersonDepartment]:
    tenant_id = require_tenant()
    person = Person.objects.for_tenant(tenant_id).filter(id=person_id).first()
    if person is None:
        raise NotFoundError("Person not found.")
    return list(person.memberships.all())


def assign_membership(
    *,
    person_id,
    department_id,
    role_id,
    start_date,
    end_date=None,
    is_primary=False,
) -> PersonDepartment:
    tenant_id = require_tenant()

    person = Person.objects.for_tenant(tenant_id).filter(id=person_id).first()
    if person is None:
        raise NotFoundError("Person not found.")

    department = (
        Department.objects.for_tenant(tenant_id).filter(id=department_id).first()
    )
    if department is None:
        raise NotFoundError("Department not found.")

    role = Role.objects.for_tenant(tenant_id).filter(id=role_id).first()
    if role is None:
        raise NotFoundError("Role not found.")

    try:
        return PersonDepartment.objects.create(
            person=person,
            department=department,
            role=role,
            start_date=start_date,
            end_date=end_date,
            is_primary=is_primary,
        )
    except IntegrityError as exc:
        raise ConflictError("Membership already exists for this start date.") from exc


def list_roles() -> list[Role]:
    tenant_id = require_tenant()
    return list(Role.objects.for_tenant(tenant_id))
