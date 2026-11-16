from rest_framework import serializers

from .models import EquivalencyQuery


class EquivalencyQuerySerializer(serializers.ModelSerializer):
    reviewer_email = serializers.CharField(source="reviewer.email", read_only=True)

    class Meta:
        model = EquivalencyQuery
        fields = [
            "id", "reviewer", "reviewer_email", "credential", "question_text",
            "answer_text", "retrieved_chunk_ids", "created_at",
        ]
        read_only_fields = ["reviewer", "answer_text", "retrieved_chunk_ids", "created_at"]
