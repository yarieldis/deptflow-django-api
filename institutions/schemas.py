import uuid

from ninja import Schema
from pydantic import ConfigDict


class InstitutionIn(Schema):
    name: str
    code: str


class InstitutionOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    is_active: bool
    parent_id: uuid.UUID | None = None


class DepartmentIn(Schema):
    name: str
    code: str


class DepartmentOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    is_active: bool
    parent_department_id: uuid.UUID | None = None
    head_person_id: uuid.UUID | None = None
