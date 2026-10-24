from rest_framework.permissions import BasePermission


class IsClient(BasePermission):
    """Autorise uniquement les comptes ayant un profil Client."""

    message = "Ce compte n'est pas un compte client."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and hasattr(user, 'client'))
 
    
def est_administrateur(user):
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


class IsAdministrateur(BasePermission):
    message = "Réservé aux administrateurs."

    def has_permission(self, request, view):
        return est_administrateur(request.user)