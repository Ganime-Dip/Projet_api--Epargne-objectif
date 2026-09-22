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
    path('tirelires/<int:pk>/', TirelireDetailView.as_view(), name='tirelire-detail'),
    path('tirelires/<int:pk>/depot/', DepotView.as_view(), name='tirelire-depot'),
    path('tirelires/<int:pk>/retrait/', RetraitView.as_view(), name='tirelire-retrait'),
    path('tirelires/<int:pk>/operations/', OperationListView.as_view(), name='tirelire-operations'),
]