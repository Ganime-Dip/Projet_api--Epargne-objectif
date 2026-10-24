from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Client, Operation, Tirelire
from .permissions import est_administrateur


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
        token['role'] = 'administrateur' if est_administrateur(user) else 'client'
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
    
class ClientSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    actif = serializers.BooleanField(source='user.is_active', read_only=True)

    class Meta:
        model = Client
        fields = (
            'id', 'username', 'email', 'telephone', 'numero_compte',
            'date_inscription', 'actif',
        )
        read_only_fields = fields


class ClientCreationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    email = serializers.EmailField(required=False, allow_blank=True)
    telephone = serializers.CharField(max_length=20)
    numero_compte = serializers.CharField(max_length=30)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur existe déjà.")
        return value

    def validate_numero_compte(self, value):
        if Client.objects.filter(numero_compte=value).exists():
            raise serializers.ValidationError("Ce numéro de compte existe déjà.")
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                password=validated_data['password'],
                email=validated_data.get('email', ''),
            )
            return Client.objects.create(
                user=user,
                telephone=validated_data['telephone'],
                numero_compte=validated_data['numero_compte'],
            )


class ClientActivationSerializer(serializers.Serializer):
    actif = serializers.BooleanField()


class AdminTirelireSerializer(TirelireSerializer):
    client_id = serializers.UUIDField(source='client.id', read_only=True)
    client_username = serializers.CharField(source='client.user.username', read_only=True)

    class Meta(TirelireSerializer.Meta):
        fields = TirelireSerializer.Meta.fields + ('client_id', 'client_username')