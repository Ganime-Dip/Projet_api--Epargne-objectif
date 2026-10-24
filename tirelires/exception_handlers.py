from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .exceptions import (
    ClientIntrouvable,
    DonneesCreationInvalides,
    MontantInvalide,
    RetraitNonAutorise,
    SoldeInsuffisant,
    TirelireIntrouvable,
)

# (type d'exception, code HTTP, message fixe ou None pour reprendre str(exc))
EXCEPTION_MAP = (
    (MontantInvalide, status.HTTP_400_BAD_REQUEST, None),
    (SoldeInsuffisant, status.HTTP_400_BAD_REQUEST, None),
    (RetraitNonAutorise, status.HTTP_400_BAD_REQUEST, None),
    (DonneesCreationInvalides, status.HTTP_400_BAD_REQUEST, None),
    (TirelireIntrouvable, status.HTTP_404_NOT_FOUND, "Tirelire introuvable."),
    (ClientIntrouvable, status.HTTP_404_NOT_FOUND, "Client introuvable."),
)

def custom_exception_handler(exc, context):
    for exc_type, code, fixed_message in EXCEPTION_MAP:
        if isinstance(exc, exc_type):
            message = fixed_message or str(exc)
            return Response({'erreur': message}, status=code)
        
    # Toute autre exception (DRF ValidationError, etc.) : comportement DRF standard
    return drf_exception_handler(exc, context)