from django.utils import timezone
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
    OperationSerializer,
    TirelireCreationSerializer,
    TirelireSerializer,
)


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
    def get(self, request):
        tirelires = request.user.client.tirelires.all()
        serializer = TirelireSerializer(tirelires, many=True)
        return Response(serializer.data)

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
    def get(self, request, pk):
        tirelire = get_tirelire_for_client(request.user.client, pk)
        return Response(TirelireSerializer(tirelire).data)


class DepotView(APIView):
    def post(self, request, pk):
        tirelire = get_tirelire_for_client(request.user.client, pk)
        serializer = DepotRetraitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tirelire.deposer(serializer.validated_data['montant'])
        return Response({'solde': tirelire.solde}, status=status.HTTP_201_CREATED)


class RetraitView(APIView):
    def post(self, request, pk):
        tirelire = get_tirelire_for_client(request.user.client, pk)
        serializer = DepotRetraitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tirelire.retirer(serializer.validated_data['montant'])
        return Response({'solde': tirelire.solde}, status=status.HTTP_201_CREATED)


class OperationListView(APIView):
    def get(self, request, pk):
        tirelire = get_tirelire_for_client(request.user.client, pk)
        operations = tirelire.operations.all()
        serializer = OperationSerializer(operations, many=True)
        return Response(serializer.data)