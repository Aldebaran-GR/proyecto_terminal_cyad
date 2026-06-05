"""URLs del módulo accounts bajo /api/v1/auth/ y /api/v1/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LoginView, MeView, ProfesorViewSet, RefreshView, UsuarioViewSet

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("profesores", ProfesorViewSet, basename="profesor")

auth_patterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
]

urlpatterns = [
    path("auth/", include(auth_patterns)),
    path("", include(router.urls)),
]
