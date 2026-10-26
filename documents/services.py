from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.errors import ConflictError, ForbiddenError, NotFoundError
from core.storage import StorageProvider
from core.tenancy import require_tenant
from documents.models import Document, DocumentType, DocumentVersion
from institutions.models import Department
from people.models import PersonDepartment
from people.services import resolve_current_person

_storage = StorageProvider()


def _active_membership_department_ids(person) -> set:
    today = timezone.localdate()
    memberships = PersonDepartment.objects.filter(
        person=person,
        start_date__lte=today,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
    return set(memberships.values_list("department_id", flat=True))


def _can_access(person, department) -> bool:
    return department.id in _active_membership_department_ids(person)


def create_document(
    request,
    *,
    department_id,
    title,
    description="",
    document_type_id=None,
    content,
    file_name,
    content_type,
    size_bytes,
) -> Document:
    tenant_id = require_tenant()
    person = resolve_current_person(request)

    department = (
        Department.objects.for_tenant(tenant_id).filter(id=department_id).first()
    )
    if department is None:
        raise NotFoundError("Department not found.")
    if not _can_access(person, department):
        raise ForbiddenError("Not an active member of this department.")

    if document_type_id is not None and not DocumentType.objects.for_tenant(
        tenant_id
    ).filter(id=document_type_id).exists():
        raise NotFoundError("Document type not found.")

    key = _storage.save(content)
    try:
        with transaction.atomic():
            document = Document.objects.create(
                institution_id=tenant_id,
                department=department,
                document_type_id=document_type_id,
                title=title,
                description=description,
                created_by_person=person,
            )
            DocumentVersion.objects.create(
                document=document,
                version_number=1,
                storage_key=key,
                file_name=file_name,
                content_type=content_type,
                size_bytes=size_bytes,
                created_by_person=person,
            )
    except Exception:
        _storage.delete(key)
        raise
    return document


def list_documents(request) -> list[Document]:
    tenant_id = require_tenant()
    person = resolve_current_person(request)
    department_ids = _active_membership_department_ids(person)
    return list(
        Document.objects.for_tenant(tenant_id).filter(department_id__in=department_ids)
    )


def get_document(request, *, document_id) -> Document:
    tenant_id = require_tenant()
    person = resolve_current_person(request)
    document = Document.objects.for_tenant(tenant_id).filter(id=document_id).first()
    if document is None:
        raise NotFoundError("Document not found.")
    if not _can_access(person, document.department):
        raise ForbiddenError("Not an active member of this department.")
    return document


def add_document_version(
    request,
    *,
    document_id,
    content,
    file_name,
    content_type,
    size_bytes,
    change_note="",
) -> DocumentVersion:
    tenant_id = require_tenant()
    person = resolve_current_person(request)

    document = Document.objects.for_tenant(tenant_id).filter(id=document_id).first()
    if document is None:
        raise NotFoundError("Document not found.")
    if not _can_access(person, document.department):
        raise ForbiddenError("Not an active member of this department.")
    if document.status != Document.Status.DRAFT:
        raise ConflictError(
            "New versions can only be added while the document is a draft."
        )

    key = _storage.save(content)
    try:
        with transaction.atomic():
            version = DocumentVersion.objects.create(
                document=document,
                version_number=document.next_version_number(),
                storage_key=key,
                file_name=file_name,
                content_type=content_type,
                size_bytes=size_bytes,
                change_note=change_note,
                created_by_person=person,
            )
    except Exception:
        _storage.delete(key)
        raise
    return version
