from rest_framework import serializers

from .models import Credential, CredentialChunk, CredentialRecord


class CredentialRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CredentialRecord
        fields = ["id", "credential", "course_or_subject", "grade_or_score", "term"]
        read_only_fields = ["credential"]


class CredentialChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CredentialChunk
        fields = ["id", "credential", "chunk_text", "chunk_index", "search_doc_id"]


class CredentialSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source="applicant.full_name", read_only=True)
    records = CredentialRecordSerializer(many=True, read_only=True)
    chunk_count = serializers.IntegerField(source="chunks.count", read_only=True)

    class Meta:
        model = Credential
        fields = [
            "id", "applicant", "applicant_name", "institution", "credential_type",
            "blob_path", "issue_date", "status", "uploaded_by", "created_at",
            "records", "chunk_count",
        ]
        read_only_fields = ["blob_path", "status", "uploaded_by", "created_at"]
