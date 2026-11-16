from rest_framework import permissions


class IsAdmissionsReviewerOrAdmin(permissions.BasePermission):
    """
    Admissions reviewers and admins may read/create/update.
    Only admins may delete. Enforced at the permission layer (and mirrored
    in get_queryset where relevant), not just hidden in the UI.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        action = getattr(view, "action", None)
        if action == "destroy":
            return user.role == user.Role.ADMIN
        return user.role in (user.Role.ADMISSIONS_REVIEWER, user.Role.ADMIN)

    def has_object_permission(self, request, view, obj):
        action = getattr(view, "action", None)
        if action == "destroy":
            return request.user.role == request.user.Role.ADMIN
        return True


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == user.Role.ADMIN)
