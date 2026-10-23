from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Operation, Tirelire


class ProgressionSerializer(serializers.Serializer):
    montant_epargne = serializers.DecimalField(max_digits=12, decimal_places=2, source='solde')
    montant_objectif = serializers.DecimalField(max_digits=12, decimal_places=2)
    montant_restant = serializers.DecimalField(max_digits=12, decimal_places=2)
    pourcentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, source='progression_pourcentage'
    )
    objectif_atteint = serializers.BooleanField()
    echeance_depassee = serializers.BooleanField()
    retrait_autorise = serializers.BooleanField()


class TirelireSerializer(serializers.ModelSerializer):
    progression = ProgressionSerializer(source='*', read_only=True)

    class Meta:
        model = Tirelire
        fields = (
            'id', 'libelle', 'montant_objectif', 'date_echeance',
            'date_ouverture', 'solde', 'progression',
        )
        read_only_fields = ('id', 'date_ouverture', 'solde')


class TirelireCreationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tirelire
        fields = ('libelle', 'montant_objectif', 'date_echeance')


class OperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operation
        fields = ('id', 'montant', 'type_operation', 'date_operation')
        read_only_fields = fields


class DepotRetraitSerializer(serializers.Serializer):
    montant = serializers.DecimalField(max_digits=12, decimal_places=2)
    

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})
    

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Ajoute l'identité et le rôle de l'utilisateur dans le token."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = 'administrateur' if user.is_staff or user.is_superuser else 'client'
        return token


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class RefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class SoldeSerializer(serializers.Serializer):
    solde = serializers.DecimalField(max_digits=12, decimal_places=2)


class ErreurSerializer(serializers.Serializer):
    erreur = serializers.CharField()


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()