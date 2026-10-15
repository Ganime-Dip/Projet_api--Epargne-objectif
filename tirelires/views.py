from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from .exceptions import AccesRefuse, DonneesCreationInvalides, TirelireIntrouvable
from .models import Tirelire
from .serializers import (
    DepotRetraitSerializer,
    DetailSerializer,
    ErreurSerializer,
    LoginSerializer,
    OperationSerializer,
    SoldeSerializer,
    TirelireCreationSerializer,
    TirelireSerializer,
    TokenSerializer,
)

R401 = OpenApiResponse(DetailSerializer, description="Token absent ou invalide.")
R403 = OpenApiResponse(ErreurSerializer, description="La tirelire appartient à un autre client (RG4).")
R404 = OpenApiResponse(ErreurSerializer, description="Tirelire introuvable.")


def get_tirelire_for_client(client, pk):
    """Récupère une tirelire en vérifiant qu'elle appartient au client (RG4).
    Correspond à la séquence 2.5 de la conception détaillée, appelée
    depuis chaque vue qui manipule une tirelire par identifiant."""
    try:
        tirelire = Tirelire.objects.get(pk=pk)
    except Tirelire.DoesNotExist:
        raise TirelireIntrouvable
    if tirelire.client != client:
        raise AccesRefuse
    return tirelire

class LoginView(ObtainAuthToken):
    @extend_schema(
        tags=['Authentification'],
        summary='Connexion',
        description="Vérifie les identifiants et retourne le token à utiliser dans l'en-tête `Authorization: Token <token>`.",
        auth=[],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(TokenSerializer, description='Connexion réussie.'),
            400: OpenApiResponse(ErreurSerializer, description='Identifiants invalides.'),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {'erreur': 'Identifiants invalides.'},
                status=HTTP_400_BAD_REQUEST,
            )
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})
    
class TirelireListCreateView(APIView):
    @extend_schema(
        tags=['Tirelires'],
        summary='Lister mes tirelires',
        description='Retourne uniquement les tirelires du client connecté (RG4).',
        responses={200: TirelireSerializer(many=True), 401: R401},
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