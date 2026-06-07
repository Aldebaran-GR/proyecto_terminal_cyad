"""Vistas de autenticación y gestión de usuarios/profesores."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
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

    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        """POST /api/v1/usuarios/{id}/set-password/ con body {"password": "..."}.

        Restablece la contraseña del usuario indicado. Solo el ADMIN puede
        llamarlo (lo garantiza permission_classes del ViewSet). Aplica los
        validadores de Django (longitud mínima, complejidad, etc.).
        """
        usuario = self.get_object()
        nueva = request.data.get("password") or ""
        if not nueva:
            raise ValidationError({"password": ["Se requiere la nueva contraseña."]})
        try:
            validate_password(nueva, user=usuario)
        except DjangoValidationError as exc:
            raise ValidationError({"password": list(exc.messages)})
        usuario.set_password(nueva)
        usuario.save(update_fields=["password"])
        return Response({"success": True})


class ProfesorViewSet(viewsets.ModelViewSet):
    """CRUD de perfiles de profesor — solo ADMIN."""

    queryset = Profesor.objects.select_related("usuario").all()
    serializer_class = ProfesorSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["estado"]
    search_fields = ["nombre_completo", "correo_institucional", "numero_economico"]

    def perform_destroy(self, instance):
        """Elimina el Profesor y su Usuario asociado.

        Los documentos creados por este profesor (Cartas Temáticas y
        Requisitos de Recuperación) se conservan: gracias a `SET_NULL`
        en sus FK y los snapshots `profesor_nombre` / `profesor_correo`,
        el historial sigue siendo legible aunque el perfil ya no exista.
        """
        with transaction.atomic():
            # Borrar primero el Usuario hace cascada al Profesor (OneToOne
            # CASCADE) y deja los documentos con profesor=NULL pero con
            # los snapshots intactos.
            usuario = instance.usuario
            if usuario:
                usuario.delete()
            else:
                instance.delete()

    @action(detail=False, methods=["post"], url_path="crear-con-usuario")
    def crear_con_usuario(self, request):
        """POST /api/v1/profesores/crear-con-usuario/

        Crea Usuario + Profesor en una sola operación **atómica**: si la
        creación del Profesor falla, el Usuario se hace rollback para no
        dejar huérfanos.

        Si ya existe un Usuario con ese email **sin perfil de Profesor**
        (huérfano de un intento anterior), se reutiliza y se le actualiza
        la contraseña con la que llega en el request — así el admin puede
        recuperarse sin tocar la BD.

        Si el email pertenece a un Usuario que **ya** tiene perfil de
        Profesor, regresa 400 explicando que el correo está en uso.

        Body:
            email, password, nombre_completo,
            numero_economico (opcional), departamento (opcional)
        """
        data = request.data
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        nombre_completo = (data.get("nombre_completo") or "").strip()
        numero_economico = data.get("numero_economico") or None
        departamento = data.get("departamento") or None

        # Validaciones de presencia
        errores = {}
        if not email:
            errores["email"] = ["El correo es obligatorio."]
        if not password:
            errores["password"] = ["La contraseña es obligatoria."]
        if not nombre_completo:
            errores["nombre_completo"] = ["El nombre completo es obligatorio."]
        if errores:
            raise ValidationError(errores)

        # Validar política de contraseña antes de tocar la BD
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            raise ValidationError({"password": list(exc.messages)})

        with transaction.atomic():
            # ¿Ya existe el usuario?
            usuario = Usuario.objects.filter(email=email).first()
            if usuario:
                # Si ya tiene perfil de profesor → conflicto real
                if Profesor.objects.filter(usuario=usuario).exists():
                    raise ValidationError({
                        "email": [
                            "Ya existe un profesor con este correo. "
                            "Usa el botón 'Contraseña' en la lista para "
                            "reestablecer su acceso."
                        ]
                    })
                # Si es huérfano (de otro rol o sin profesor), lo
                # reutilizamos: actualizamos rol/nombre y nueva contraseña.
                usuario.rol = Usuario.Rol.PROFESOR
                usuario.nombre = nombre_completo
                usuario.is_active = True
                usuario.set_password(password)
                usuario.save()
            else:
                usuario = Usuario(
                    email=email,
                    nombre=nombre_completo,
                    rol=Usuario.Rol.PROFESOR,
                )
                usuario.set_password(password)
                usuario.save()

            # Crear el Profesor en el mismo bloque atómico
            try:
                profesor = Profesor.objects.create(
                    usuario=usuario,
                    nombre_completo=nombre_completo,
                    correo_institucional=email,
                    numero_economico=numero_economico,
                    departamento_id=departamento,
                )
            except Exception as exc:
                # Cualquier error aquí dispara rollback de TODO incluyendo
                # el Usuario, así no quedan huérfanos.
                raise ValidationError({
                    "non_field_errors": [str(exc) or "Error al crear el perfil del profesor."]
                })

        serializer = ProfesorSerializer(profesor)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
