from django.urls import path

from .views import (
    DepotView,
    LoginView,
    LogoutView,
    OperationListView,
    RefreshView,
    RetraitView,
    TirelireDetailView,
    TirelireListCreateView,
)

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', RefreshView.as_view(), name='token-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('tirelires/', TirelireListCreateView.as_view(), name='tirelire-list-create'),
    path('tirelires/<uuid:pk>/', TirelireDetailView.as_view(), name='tirelire-detail'),
    path('tirelires/<uuid:pk>/depot/', DepotView.as_view(), name='tirelire-depot'),
    path('tirelires/<uuid:pk>/retrait/', RetraitView.as_view(), name='tirelire-retrait'),
    path('tirelires/<uuid:pk>/operations/', OperationListView.as_view(), name='tirelire-operations'),
]