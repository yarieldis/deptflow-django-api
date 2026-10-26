from django.db import models

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
