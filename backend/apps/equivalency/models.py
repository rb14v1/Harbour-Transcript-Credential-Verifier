from django.conf import settings
from django.db import models

from apps.credentials.models import Credential


class EquivalencyQuery(models.Model):
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="equivalency_queries",
    )
    credential = models.ForeignKey(
        Credential,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="equivalency_queries",
    )
    question_text = models.TextField()
    answer_text = models.TextField(blank=True, default="")
    retrieved_chunk_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "equivalency queries"

    def __str__(self) -> str:
        return self.question_text[:60]
