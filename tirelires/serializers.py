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