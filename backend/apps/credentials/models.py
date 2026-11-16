from django.conf import settings
from django.db import models

from apps.applicants.models import Applicant


class Credential(models.Model):
    class CredentialType(models.TextChoices):
        TRANSCRIPT = "transcript", "Transcript"
        CERTIFICATE = "certificate", "Certificate"
        DIPLOMA = "diploma", "Diploma"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSED = "processed", "Processed"

    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name="credentials")
    institution = models.CharField(max_length=255)
    credential_type = models.CharField(max_length=32, choices=CredentialType.choices)
    blob_path = models.CharField(max_length=500, blank=True, default="")
    issue_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.UPLOADED)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_credentials",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.institution} {self.credential_type} ({self.applicant.full_name})"


class CredentialRecord(models.Model):
    credential = models.ForeignKey(Credential, on_delete=models.CASCADE, related_name="records")
    course_or_subject = models.CharField(max_length=255)
    grade_or_score = models.CharField(max_length=50, blank=True, default="")
    term = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.course_or_subject


class CredentialChunk(models.Model):
    credential = models.ForeignKey(Credential, on_delete=models.CASCADE, related_name="chunks")
    chunk_text = models.TextField()
    chunk_index = models.PositiveIntegerField()
    search_doc_id = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ["chunk_index"]

    def __str__(self) -> str:
        return self.search_doc_id
