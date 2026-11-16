from django.contrib.auth import get_user_model
from rest_framework import mixins, permissions, viewsets

from apps.credentials import services
from apps.users.permissions import IsAdmissionsReviewerOrAdmin

from .models import EquivalencyQuery
from .serializers import EquivalencyQuerySerializer

User = get_user_model()


class EquivalencyQueryViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Ask + list history. Reviewers only see their own history; admins see all."""

    serializer_class = EquivalencyQuerySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmissionsReviewerOrAdmin]

    def get_queryset(self):
        qs = EquivalencyQuery.objects.select_related("reviewer", "credential").all()
        user = self.request.user
        if user.role != User.Role.ADMIN:
            qs = qs.filter(reviewer=user)
        return qs

    def perform_create(self, serializer):
        credential = serializer.validated_data.get("credential")
        question_text = serializer.validated_data.get("question_text")
        answer_text, retrieved_chunk_ids = services.answer_equivalency_question(
            question_text, credential=credential
        )
        serializer.save(
            reviewer=self.request.user,
            answer_text=answer_text,
            retrieved_chunk_ids=retrieved_chunk_ids,
        )
