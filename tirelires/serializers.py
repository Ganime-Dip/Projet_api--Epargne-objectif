from rest_framework import serializers

from .models import Operation, Tirelire


class TirelireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tirelire
        fields = (
            'id', 'libelle', 'montant_objectif', 'date_echeance',
            'date_ouverture', 'solde',
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
    

class TokenSerializer(serializers.Serializer):
    token = serializers.CharField()


class SoldeSerializer(serializers.Serializer):
    solde = serializers.DecimalField(max_digits=12, decimal_places=2)


class ErreurSerializer(serializers.Serializer):
    erreur = serializers.CharField()


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()