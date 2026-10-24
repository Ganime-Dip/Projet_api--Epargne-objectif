from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .exceptions import DonneesCreationInvalides, TirelireIntrouvable
from .filters import OperationFilter, RechercheFilter, TirelireFilter, TriFilter
from .models import Operation, Tirelire
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
    
class StableOrderingMixin:
    """Ajoute l'id comme dernier critère de tri : sans cela, la pagination peut
    répéter ou sauter des éléments quand plusieurs lignes ont la même valeur de tri."""

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset.order_by(*queryset.query.order_by, 'id')

class TirelireListCreateView(StableOrderingMixin, generics.ListCreateAPIView):
    serializer_class = TirelireSerializer
    filter_backends = [DjangoFilterBackend, RechercheFilter, TriFilter]
    filterset_class = TirelireFilter
    search_fields = ['libelle']
    ordering_fields = [
        'libelle', 'date_echeance', 'date_ouverture', 'solde', 'montant_objectif',
    ]
    ordering = ['-date_ouverture']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Tirelire.objects.none()
        return self.request.user.client.tirelires.all()

    @extend_schema(
        tags=['Tirelires'],
        summary='Lister mes tirelires',
        description=(
            "Liste paginée des tirelires du client connecté (RG4). "
            "Recherche par libellé (`search`), filtres et tri (`ordering`, préfixe `-` pour décroissant)."
        ),
        responses={200: TirelireSerializer(many=True), 401: R401, 403: R403},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

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


class OperationListView(StableOrderingMixin, generics.ListAPIView):
    serializer_class = OperationSerializer
    filter_backends = [DjangoFilterBackend, TriFilter]
    filterset_class = OperationFilter
    ordering_fields = ['date_operation', 'montant']
    ordering = ['-date_operation']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Operation.objects.none()
        tirelire = get_tirelire_for_client(self.request.user.client, self.kwargs['pk'])
        return tirelire.operations.all()

    @extend_schema(
        tags=['Opérations'],
        summary="Historique des opérations d'une tirelire",
        description="Liste paginée, de la plus récente à la plus ancienne par défaut, avec filtres et tri.",
        responses={200: OperationSerializer(many=True), 401: R401, 403: R403, 404: R404},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)