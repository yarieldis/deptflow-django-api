from django.db import models
from django.utils import timezone

from core.errors import InvalidStateError
from core.models import TenantModel, UUIDModel


class DocumentType(TenantModel):
    """Per-institution document categorization."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Document(TenantModel):
    """Department-owned document metadata and workflow status.

    The workflow is document-level: ``Draft → PendingApproval → Approved →
    Published`` with ``Archived`` terminal. Versioning is publish-count based
    (``Major.Minor``); individual file uploads live on ``DocumentVersion``.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "PendingApproval"
        APPROVED = "approved", "Approved"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    department = models.ForeignKey(
        "institutions.Department", on_delete=models.RESTRICT, related_name="documents"
    )
    document_type = models.ForeignKey(
        DocumentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.DRAFT
    )

    # Publish-count versioning (Major.Minor)
    major_version = models.PositiveIntegerField(default=0)
    minor_version = models.PositiveIntegerField(default=0)
    published_version = models.ForeignKey(
        "DocumentVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    created_by_person = models.ForeignKey(
        "people.Person", on_delete=models.RESTRICT, related_name="+"
    )

    # Workflow audit fields (document-level)
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    review_comment = models.TextField(blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    unpublished_at = models.DateTimeField(null=True, blank=True)
    unpublished_by_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    unpublish_reason = models.TextField(blank=True, default="")
    requires_new_upload = models.BooleanField(default=False)
    requires_new_upload_from_version = models.ForeignKey(
        "DocumentVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def latest_version(self):
        return self.versions.order_by("-version_number").first()

    def next_version_number(self) -> int:
        latest = self.latest_version
        return (latest.version_number + 1) if latest else 1

    @property
    def version(self) -> str:
        """The ``Major.Minor`` publish version."""
        return f"{self.major_version}.{self.minor_version}"

    # --- Workflow state machine (guarded; mutate only through these methods) ---

    def submit(self, by_person):
        if self.status != self.Status.DRAFT:
            raise InvalidStateError("Only draft documents can be submitted.")
        if self.requires_new_upload:
            raise InvalidStateError("A new upload is required before resubmitting.")
        self.status = self.Status.PENDING_APPROVAL
        self.submitted_at = timezone.now()
        self.submitted_by_person = by_person

    def approve(self, by_person, comment=""):
        if self.status != self.Status.PENDING_APPROVAL:
            raise InvalidStateError("Only pending documents can be approved.")
        latest = self.latest_version
        if latest is not None and latest.created_by_person_id == by_person.pk:
            raise InvalidStateError("The uploader cannot approve their own document.")
        self.status = self.Status.APPROVED
        self.reviewed_at = timezone.now()
        self.reviewed_by_person = by_person
        self.review_comment = comment

    def reject(self, by_person, comment, requires_new_upload=False):
        if self.status != self.Status.PENDING_APPROVAL:
            raise InvalidStateError("Only pending documents can be rejected.")
        if not comment or not comment.strip():
            raise InvalidStateError("A comment is required to reject a document.")
        self.status = self.Status.DRAFT
        self.reviewed_at = timezone.now()
        self.reviewed_by_person = by_person
        self.review_comment = comment
        if requires_new_upload:
            self.requires_new_upload = True
            self.requires_new_upload_from_version = self.latest_version
        else:
            self.requires_new_upload = False
            self.requires_new_upload_from_version = None

    def publish(self, by_person):
        if self.status != self.Status.APPROVED:
            raise InvalidStateError("Only approved documents can be published.")
        latest = self.latest_version
        if latest is None:
            raise InvalidStateError("A document must have a version to be published.")
        if self.published_version_id is None or self.published_version_id != latest.pk:
            # New content under review → bump major, reset minor.
            self.major_version += 1
            self.minor_version = 0
            self.published_version = latest
        else:
            # Same content re-approved → bump minor.
            self.minor_version += 1
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.published_by_person = by_person

    def unpublish(self, by_person, reason):
        if self.status != self.Status.PUBLISHED:
            raise InvalidStateError("Only published documents can be unpublished.")
        if not reason or not reason.strip():
            raise InvalidStateError("A reason is required to unpublish a document.")
        self.status = self.Status.PENDING_APPROVAL
        self.unpublished_at = timezone.now()
        self.unpublished_by_person = by_person
        self.unpublish_reason = reason

    def archive(self, by_person):
        if self.status == self.Status.ARCHIVED:
            raise InvalidStateError("Document is already archived.")
        if self.published_version_id is None:
            raise InvalidStateError(
                "Only documents that have been published can be archived."
            )
        self.status = self.Status.ARCHIVED


class DocumentVersion(UUIDModel):
    """Immutable file facts for one upload of a document.

    No workflow status lives here — versions are pure file history. The upload
    ordinal (``version_number``) is unique per document.
    """

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=500)
    storage_provider = models.CharField(max_length=50, blank=True, default="")
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size_bytes = models.PositiveBigIntegerField()
    change_note = models.TextField(blank=True, default="")
    created_by_person = models.ForeignKey(
        "people.Person", on_delete=models.RESTRICT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_number"],
                name="uniq_version_number_per_document",
            )
        ]

    def __str__(self) -> str:
        return f"{self.document.title} v{self.version_number}"
