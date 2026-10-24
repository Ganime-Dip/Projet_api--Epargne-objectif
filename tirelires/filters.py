from django.db.models import F, Q
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Operation, Tirelire


class TirelireFilter(filters.FilterSet):
    montant_objectif_min = filters.NumberFilter(
        field_name='montant_objectif', lookup_expr='gte',
        help_text="Montant objectif minimum.",
    )
    montant_objectif_max = filters.NumberFilter(
        field_name='montant_objectif', lookup_expr='lte',
        help_text="Montant objectif maximum.",
    )
    echeance_apres = filters.DateFilter(
        field_name='date_echeance', lookup_expr='gte',
        help_text="Échéance à partir de cette date (AAAA-MM-JJ).",
    )
    echeance_avant = filters.DateFilter(
        field_name='date_echeance', lookup_expr='lte',
        help_text="Échéance jusqu'à cette date (AAAA-MM-JJ).",
    )
    objectif_atteint = filters.BooleanFilter(
        method='filter_objectif_atteint',
        help_text="true : solde ≥ objectif ; false : solde < objectif.",
    )
    echeance_depassee = filters.BooleanFilter(
        method='filter_echeance_depassee',
        help_text="true : échéance passée ; false : échéance à venir ou du jour.",
    )
    retrait_autorise = filters.BooleanFilter(
        method='filter_retrait_autorise',
        help_text="true : objectif atteint ou échéance dépassée (RG3) ; false : retrait bloqué.",
    )

    class Meta:
        model = Tirelire
        fields = []

    def filter_objectif_atteint(self, queryset, name, value):
        if value:
            return queryset.filter(solde__gte=F('montant_objectif'))
        return queryset.filter(solde__lt=F('montant_objectif'))

    def filter_echeance_depassee(self, queryset, name, value):
        aujourd_hui = timezone.now().date()
        if value:
            return queryset.filter(date_echeance__lt=aujourd_hui)
        return queryset.filter(date_echeance__gte=aujourd_hui)

    def filter_retrait_autorise(self, queryset, name, value):
        condition = Q(solde__gte=F('montant_objectif')) | Q(
            date_echeance__lt=timezone.now().date()
        )
        return queryset.filter(condition) if value else queryset.exclude(condition)


class OperationFilter(filters.FilterSet):
    type_operation = filters.ChoiceFilter(
        choices=Operation.TYPE_CHOICES, help_text="depot ou retrait."
    )
    date_apres = filters.DateFilter(
        field_name='date_operation', lookup_expr='date__gte',
        help_text="Opérations à partir de cette date (AAAA-MM-JJ).",
    )
    date_avant = filters.DateFilter(
        field_name='date_operation', lookup_expr='date__lte',
        help_text="Opérations jusqu'à cette date (AAAA-MM-JJ).",
    )
    montant_min = filters.NumberFilter(
        field_name='montant', lookup_expr='gte', help_text="Montant minimum."
    )
    montant_max = filters.NumberFilter(
        field_name='montant', lookup_expr='lte', help_text="Montant maximum."
    )

    class Meta:
        model = Operation
        fields = []
        
class TriFilter(OrderingFilter):
    """Tri avec description en français, listant les champs réellement acceptés."""

    def get_schema_operation_parameters(self, view):
        parametres = super().get_schema_operation_parameters(view)
        champs = ', '.join(view.ordering_fields)
        for parametre in parametres:
            parametre['description'] = (
                f"Champ de tri, parmi : {champs}. "
                f"Préfixer par « - » pour un tri décroissant (ex. -{view.ordering_fields[0]})."
            )
        return parametres


class RechercheFilter(SearchFilter):
    search_description = "Recherche dans le libellé de la tirelire."