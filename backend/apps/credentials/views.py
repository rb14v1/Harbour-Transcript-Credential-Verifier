from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.common import blob_store
from apps.users.permissions import IsAdmissionsReviewerOrAdmin

from . import services
from .models import Credential
from .serializers import CredentialRecordSerializer, CredentialSerializer


class CredentialViewSet(viewsets.ModelViewSet):
    queryset = Credential.objects.select_related("applicant").all().order_by("-created_at")
    serializer_class = CredentialSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmissionsReviewerOrAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        applicant_id = self.request.query_params.get("applicant")
        if applicant_id:
            qs = qs.filter(applicant_id=applicant_id)
        return qs

    def perform_create(self, serializer):
        file_obj = self.request.FILES.get("file")
        credential = serializer.save(uploaded_by=self.request.user, status=Credential.Status.UPLOADED)
        if file_obj is not None:
            blob_path = blob_store.upload_document(
                file_obj,
                container="credentials",
                blob_name=f"credential_{credential.id}_{file_obj.name}",
            )
            credential.blob_path = blob_path
            credential.save(update_fields=["blob_path"])

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        credential = self.get_object()
        if not credential.blob_path:
            return Response({"detail": "No document uploaded for this credential yet."}, status=400)
        services.process_credential(credential)
        credential.refresh_from_db()
        return Response(self.get_serializer(credential).data)

    @action(detail=True, methods=["get"])
    def records(self, request, pk=None):
        credential = self.get_object()
        serializer = CredentialRecordSerializer(credential.records.all(), many=True)
        return Response(serializer.data)
