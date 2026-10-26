import uuid
from datetime import datetime

from ninja import Schema
from pydantic import ConfigDict


class DocumentOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    status: str
    department_id: uuid.UUID
    document_type_id: uuid.UUID | None = None
    major_version: int
    minor_version: int
    created_by_person_id: uuid.UUID
    created_at: datetime


class VersionOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    storage_key: str
    file_name: str
    content_type: str
    size_bytes: int
    change_note: str
    created_by_person_id: uuid.UUID
    created_at: datetime


class DocumentDetailOut(Schema):
    id: uuid.UUID
    title: str
    description: str
    status: str
    department_id: uuid.UUID
    document_type_id: uuid.UUID | None = None
    major_version: int
    minor_version: int
    created_by_person_id: uuid.UUID
    created_at: datetime
    versions: list[VersionOut]
