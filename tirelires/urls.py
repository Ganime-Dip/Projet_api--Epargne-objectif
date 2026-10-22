from django.urls import path

from .views import (
    DepotView,
    LoginView,
    OperationListView,
    RetraitView,
    TirelireDetailView,
    TirelireListCreateView,
)

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('tirelires/', TirelireListCreateView.as_view(), name='tirelire-list-create'),
    path('tirelires/<uuid:pk>/', TirelireDetailView.as_view(), name='tirelire-detail'),
    path('tirelires/<uuid:pk>/depot/', DepotView.as_view(), name='tirelire-depot'),
    path('tirelires/<uuid:pk>/retrait/', RetraitView.as_view(), name='tirelire-retrait'),
    path('tirelires/<uuid:pk>/operations/', OperationListView.as_view(), name='tirelire-operations'),
]