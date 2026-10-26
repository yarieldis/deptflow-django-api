import uuid
from datetime import date

from ninja import Schema
from pydantic import ConfigDict, Field


class PersonIn(Schema):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str = ""
    phone: str = ""
    job_title: str = ""


class PersonUpdate(Schema):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    job_title: str | None = None


class PersonOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str
    job_title: str
    is_active: bool
    user_id: uuid.UUID | None = None


class RoleOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    can_approve_documents: bool
    can_publish_documents: bool
    is_active: bool


class MembershipIn(Schema):
    person_id: uuid.UUID
    department_id: uuid.UUID
    role_id: uuid.UUID
    start_date: date
    end_date: date | None = None
    is_primary: bool = False


class MembershipOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_id: uuid.UUID
    department_id: uuid.UUID
    role_id: uuid.UUID
    is_primary: bool
    start_date: date
    end_date: date | None = None
