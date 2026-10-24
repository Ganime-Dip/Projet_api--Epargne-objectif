from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_description = "Numéro de la page à afficher."
    page_size_query_description = "Nombre de résultats par page (10 par défaut, 100 maximum)."