from rest_framework import serializers

from .models import Applicant


class ApplicantSerializer(serializers.ModelSerializer):
    credential_count = serializers.IntegerField(source="credentials.count", read_only=True)

    class Meta:
        model = Applicant
        fields = ["id", "full_name", "email", "created_at", "credential_count"]
        read_only_fields = ["created_at"]
