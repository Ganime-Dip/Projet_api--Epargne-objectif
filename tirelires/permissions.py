from rest_framework.permissions import BasePermission


class IsClient(BasePermission):
    """Autorise uniquement les comptes ayant un profil Client."""

    message = "Ce compte n'est pas un compte client."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and hasattr(user, 'client'))