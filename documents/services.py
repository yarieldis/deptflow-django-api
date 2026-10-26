from django.db import transaction

from core.errors import ConflictError, ForbiddenError, NotFoundError
from core.storage import StorageProvider
from core.tenancy import require_tenant
from documents.models import Document, DocumentType, DocumentVersion
from documents.policy import DocumentAccessPolicy
from institutions.models import Department
from people.services import resolve_current_person

_storage = StorageProvider()
_policy = DocumentAccessPolicy()


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
    if not _policy.can_access(person, department):
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
    department_ids = DocumentAccessPolicy.active_department_ids(person)
    return list(
        Document.objects.for_tenant(tenant_id).filter(department_id__in=department_ids)
    )


def get_document(request, *, document_id) -> Document:
    tenant_id = require_tenant()
    person = resolve_current_person(request)
    document = Document.objects.for_tenant(tenant_id).filter(id=document_id).first()
    if document is None:
        raise NotFoundError("Document not found.")
    if not _policy.can_access(person, document.department):
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
    if not _policy.can_access(person, document.department):
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
            # A new upload clears the requires-new-upload gate.
            document.requires_new_upload = False
            document.requires_new_upload_from_version = None
            document.save(
                update_fields=[
                    "requires_new_upload",
                    "requires_new_upload_from_version",
                    "updated_at",
                ]
            )
    except Exception:
        _storage.delete(key)
        raise
    return version


def _locked_document(tenant_id, document_id):
    return (
        Document.objects.for_tenant(tenant_id)
        .select_for_update()
        .filter(id=document_id)
        .first()
    )


def submit_document(request, *, document_id) -> Document:
    tenant_id = require_tenant()
    person = resolve_current_person(request)
    with transaction.atomic():
        document = _locked_document(tenant_id, document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        if not _policy.can_submit(person, document):
            raise ForbiddenError("Not allowed to submit this document.")
        document.submit(person)
        document.save()
    return document


def approve_document(request, *, document_id, comment="") -> Document:
    tenant_id = require_tenant()
    person = resolve_current_person(request)
    with transaction.atomic():
        document = _locked_document(tenant_id, document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        if not _policy.can_approve(person, document):
            raise ForbiddenError("Not allowed to approve this document.")
        document.approve(person, comment=comment)
        document.save()
    return document


def reject_document(
    request, *, document_id, comment, requires_new_upload=False
) -> Document:
    tenant_id = require_tenant()
    person = resolve_current_person(request)
    with transaction.atomic():
        document = _locked_document(tenant_id, document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        if not _policy.can_review(person, document):
            raise ForbiddenError("Not allowed to reject this document.")
        document.reject(person, comment=comment, requires_new_upload=requires_new_upload)
        document.save()
    return document


def publish_document(request, *, document_id) -> Document:
    tenant_id = require_tenant()
    person = resolve_current_person(request)
    with transaction.atomic():
        document = _locked_document(tenant_id, document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        if not _policy.can_publish(person, document):
            raise ForbiddenError("Not allowed to publish this document.")
        document.publish(person)
        document.save()
    return document


def unpublish_document(request, *, document_id, reason) -> Document:
    tenant_id = require_tenant()
    person = resolve_current_person(request)
    with transaction.atomic():
        document = _locked_document(tenant_id, document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        if not _policy.can_publish(person, document):
            raise ForbiddenError("Not allowed to unpublish this document.")
        document.unpublish(person, reason=reason)
        document.save()
    return document


def archive_document(request, *, document_id) -> Document:
    tenant_id = require_tenant()
    person = resolve_current_person(request)
    with transaction.atomic():
        document = _locked_document(tenant_id, document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        if not _policy.can_archive(person, document):
            raise ForbiddenError("Not allowed to archive this document.")
        document.archive(person)
        document.save()
    return document
