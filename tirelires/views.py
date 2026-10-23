from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .exceptions import DonneesCreationInvalides, TirelireIntrouvable
from .models import Tirelire
from .serializers import (
    CustomTokenObtainPairSerializer,
    DepotRetraitSerializer,
    DetailSerializer,
    ErreurSerializer,
    LoginSerializer,
    OperationSerializer,
    RefreshRequestSerializer,
    SoldeSerializer,
    TirelireCreationSerializer,
    TirelireSerializer,
    TokenPairSerializer,
)

R401 = OpenApiResponse(DetailSerializer, description="Token absent, invalide ou expiré.")
R403 = OpenApiResponse(DetailSerializer, description="Compte sans profil client (ex. administrateur).")
R404 = OpenApiResponse(ErreurSerializer, description="Tirelire introuvable (inexistante ou n'appartenant pas au client).")


def get_tirelire_for_client(client, pk):
    """Recherche la tirelire parmi celles du client connecté (RG4).
    Une tirelire inexistante ou appartenant à un autre client donne la même
    réponse (404), pour ne jamais révéler son existence."""
    try:
        return client.tirelires.get(pk=pk)
    except Tirelire.DoesNotExist:
        raise TirelireIntrouvable

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        tags=['Authentification'],
        summary='Connexion',
        description=(
            "Vérifie les identifiants et retourne un access token (15 min) et un refresh token (1 jour). "
            "Une nouvelle paire est générée à chaque connexion. "
            "Utiliser l'access token dans Authorize."
        ),
        auth=[],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(TokenPairSerializer, description='Connexion réussie.'),
            400: OpenApiResponse(ErreurSerializer, description='Identifiants invalides.'),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (AuthenticationFailed, TokenError):
            return Response({'erreur': 'Identifiants invalides.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentification'],
    summary='Renouveler la session',
    description=(
        "Échange un refresh token valide contre un nouvel access token et un nouveau refresh token. "
        "L'ancien refresh token devient inutilisable."
    ),
    auth=[],
    request=RefreshRequestSerializer,
    responses={
        200: OpenApiResponse(TokenPairSerializer, description='Nouvelle paire de tokens.'),
        401: OpenApiResponse(DetailSerializer, description='Refresh token invalide, expiré ou déjà utilisé.'),
    },
)
class RefreshView(TokenRefreshView):
    pass


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Authentification'],
        summary='Déconnexion',
        description=(
            "Invalide le refresh token fourni : il ne permettra plus de renouveler la session. "
            "L'access token en cours reste valide jusqu'à son expiration (15 minutes maximum)."
        ),
        request=RefreshRequestSerializer,
        responses={
            204: OpenApiResponse(description='Déconnexion effectuée.'),
            400: OpenApiResponse(ErreurSerializer, description='Refresh token invalide ou appartenant à un autre compte.'),
            401: R401,
        },
    )
    def post(self, request):
        serializer = RefreshRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            if str(token['user_id']) != str(request.user.pk):
                raise TokenError('Token appartenant à un autre compte')
            token.blacklist()
        except TokenError:
            return Response({'erreur': 'Refresh token invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class TirelireListCreateView(APIView):
    @extend_schema(
        tags=['Tirelires'],
        summary='Lister mes tirelires',
        description='Retourne uniquement les tirelires du client connecté (RG4).',
        responses={200: TirelireSerializer(many=True), 401: R401, 403: R403},
    )
    def get(self, request):
        tirelires = request.user.client.tirelires.all()
        serializer = TirelireSerializer(tirelires, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Tirelires'],
        summary='Créer une tirelire',
        description='Crée une tirelire avec un solde initial nul.',
        request=TirelireCreationSerializer,
        responses={
            201: OpenApiResponse(TirelireSerializer, description='Tirelire créée.'),
            400: OpenApiResponse(ErreurSerializer, description="Montant objectif ≤ 0 (RG5) ou date d'échéance non future (RG6)."),
            401: R401,
            403: R403,
        },
    )
    def post(self, request):
        serializer = TirelireCreationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        montant_objectif = serializer.validated_data['montant_objectif']
        date_echeance = serializer.validated_data['date_echeance']

        if montant_objectif <= 0:
            raise DonneesCreationInvalides("Le montant objectif doit être positif.")
        if date_echeance <= timezone.now().date():
            raise DonneesCreationInvalides("La date d'échéance doit être future.")

        tirelire = Tirelire.objects.create(
            client=request.user.client,
            libelle=serializer.validated_data['libelle'],
            montant_objectif=montant_objectif,
            date_echeance=date_echeance,
        )
        return Response(TirelireSerializer(tirelire).data, status=status.HTTP_201_CREATED)


class TirelireDetailView(APIView):
    @extend_schema(
        tags=['Tirelires'],
        summary="Consulter une tirelire",
        description="Retourne le détail de la tirelire, avec sa progression : montant épargné, objectif, montant restant, pourcentage et état du blocage des retraits.",
        responses={200: TirelireSerializer, 401: R401, 403: R403, 404: R404},
    )
    def get(self, request, pk):
        tirelire = get_tirelire_for_client(request.user.client, pk)
        return Response(TirelireSerializer(tirelire).data)


class DepotView(APIView):
    @extend_schema(
        tags=['Opérations'],
        summary='Effectuer un dépôt',
        description='Le montant doit être strictement positif (RG1).',
        request=DepotRetraitSerializer,
        responses={
            201: OpenApiResponse(SoldeSerializer, description='Dépôt enregistré, nouveau solde retourné.'),
            400: OpenApiResponse(ErreurSerializer, description='Montant invalide (RG1).'),
            401: R401, 403: R403, 404: R404,
        },
    )
    def post(self, request, pk):
        tirelire = get_tirelire_for_client(request.user.client, pk)
        serializer = DepotRetraitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tirelire.deposer(serializer.validated_data['montant'])
        return Response({'solde': tirelire.solde}, status=status.HTTP_201_CREATED)


class RetraitView(APIView):
    @extend_schema(
        tags=['Opérations'],
        summary='Effectuer un retrait',
        description="Vérifié dans l'ordre : montant strictement positif (RG1), solde suffisant (RG2), objectif atteint ou échéance dépassée (RG3).",
        request=DepotRetraitSerializer,
        responses={
            201: OpenApiResponse(SoldeSerializer, description='Retrait enregistré, nouveau solde retourné.'),
            400: OpenApiResponse(ErreurSerializer, description='Montant invalide (RG1), solde insuffisant (RG2) ou retrait non autorisé (RG3).'),
            401: R401, 403: R403, 404: R404,
        },
    )
    def post(self, request, pk):
        tirelire = get_tirelire_for_client(request.user.client, pk)
        serializer = DepotRetraitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tirelire.retirer(serializer.validated_data['montant'])
        return Response({'solde': tirelire.solde}, status=status.HTTP_201_CREATED)


class OperationListView(APIView):
    @extend_schema(
        tags=['Opérations'],
        summary="Historique des opérations d'une tirelire",
        responses={200: OperationSerializer(many=True), 401: R401, 403: R403, 404: R404},
    )
    def get(self, request, pk):
        tirelire = get_tirelire_for_client(request.user.client, pk)
        operations = tirelire.operations.all()
        serializer = OperationSerializer(operations, many=True)
        return Response(serializer.data)