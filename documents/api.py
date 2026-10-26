import uuid

from ninja import File, Form, Router
from ninja.files import UploadedFile

from documents import services
from documents.schemas import (
    ApproveIn,
    DocumentDetailOut,
    DocumentOut,
    RejectIn,
    UnpublishIn,
    VersionOut,
)

router = Router()


@router.post("/documents", response=DocumentOut)
def create_document(
    request,
    department_id: uuid.UUID = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    document_type_id: uuid.UUID | None = Form(None),
    file: UploadedFile = File(...),
):
    content = file.read()
    return services.create_document(
        request,
        department_id=department_id,
        title=title,
        description=description,
        document_type_id=document_type_id,
        content=content,
        file_name=file.name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
    )


@router.get("/documents", response=list[DocumentOut])
def list_documents(request):
    return services.list_documents(request)


@router.get("/documents/{document_id}", response=DocumentDetailOut)
def get_document(request, document_id: uuid.UUID):
    doc = services.get_document(request, document_id=document_id)
    return {
        "id": doc.id,
        "title": doc.title,
        "description": doc.description,
        "status": doc.status,
        "department_id": doc.department_id,
        "document_type_id": doc.document_type_id,
        "major_version": doc.major_version,
        "minor_version": doc.minor_version,
        "created_by_person_id": doc.created_by_person_id,
        "created_at": doc.created_at,
        "versions": list(doc.versions.all()),
    }


@router.post("/documents/{document_id}/versions", response=VersionOut)
def add_document_version(
    request,
    document_id: uuid.UUID,
    file: UploadedFile = File(...),
    change_note: str = Form(""),
):
    content = file.read()
    return services.add_document_version(
        request,
        document_id=document_id,
        content=content,
        file_name=file.name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        change_note=change_note,
    )


@router.post("/documents/{document_id}/submit", response=DocumentOut)
def submit_document(request, document_id: uuid.UUID):
    return services.submit_document(request, document_id=document_id)


@router.post("/documents/{document_id}/approve", response=DocumentOut)
def approve_document(request, document_id: uuid.UUID, payload: ApproveIn):
    return services.approve_document(
        request, document_id=document_id, comment=payload.comment
    )


@router.post("/documents/{document_id}/reject", response=DocumentOut)
def reject_document(request, document_id: uuid.UUID, payload: RejectIn):
    return services.reject_document(
        request,
        document_id=document_id,
        comment=payload.comment,
        requires_new_upload=payload.requires_new_upload,
    )


@router.post("/documents/{document_id}/publish", response=DocumentOut)
def publish_document(request, document_id: uuid.UUID):
    return services.publish_document(request, document_id=document_id)


@router.post("/documents/{document_id}/unpublish", response=DocumentOut)
def unpublish_document(request, document_id: uuid.UUID, payload: UnpublishIn):
    return services.unpublish_document(
        request, document_id=document_id, reason=payload.reason
    )


@router.post("/documents/{document_id}/archive", response=DocumentOut)
def archive_document(request, document_id: uuid.UUID):
    return services.archive_document(request, document_id=document_id)
