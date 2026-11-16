from rest_framework import permissions, viewsets

from apps.users.permissions import IsAdmissionsReviewerOrAdmin

from .models import Applicant
from .serializers import ApplicantSerializer


class ApplicantViewSet(viewsets.ModelViewSet):
    queryset = Applicant.objects.all().order_by("-created_at")
    serializer_class = ApplicantSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmissionsReviewerOrAdmin]
