"""Vistas de autenticación y gestión de usuarios/profesores."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.permissions import IsAdmin

from .models import Profesor, Usuario
from .serializers import (
    CustomTokenObtainPairSerializer,
    MeSerializer,
    ProfesorSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
)


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — Devuelve access+refresh+datos del usuario."""

    serializer_class = CustomTokenObtainPairSerializer


class RefreshView(TokenRefreshView):
    """POST /api/v1/auth/refresh/ — Renueva el access token."""


class MeView(APIView):
    """GET /api/v1/auth/me/ — Datos del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response({"success": True, "data": serializer.data})


class UsuarioViewSet(viewsets.ModelViewSet):
    """CRUD de usuarios — solo ADMIN."""

    queryset = Usuario.objects.all().order_by("nombre")
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["rol", "is_active"]
    search_fields = ["email", "nombre"]

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer
        return UsuarioSerializer

    @action(detail=True, methods=["post"], url_path="toggle-activo")
    def toggle_activo(self, request, pk=None):
        usuario = self.get_object()
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=["is_active"])
        return Response({"success": True, "is_active": usuario.is_active})


class ProfesorViewSet(viewsets.ModelViewSet):
    """CRUD de perfiles de profesor — solo ADMIN."""

    queryset = Profesor.objects.select_related("usuario").all()
    serializer_class = ProfesorSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["estado"]
    search_fields = ["nombre_completo", "correo_institucional", "numero_economico"]
