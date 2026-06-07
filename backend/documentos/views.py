"""ViewSets de documentos académicos con reglas de propiedad y estado.

Adicionalmente se exponen dos `RetrieveAPIView` públicas (sin auth, AllowAny)
para consultar Carta Temática / Evaluación de Recuperación en estado PUBLICADO.
"""

from django.db import IntegrityError

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from catalogos.models import Periodo
from core.permissions import IsOwnerProfesorOrAdminReadOnly

from .models import CartaTematica, RequisitoRecuperacion
from .serializers import (
    CartaTematicaSerializer,
    PublicCartaTematicaSerializer,
    PublicDocumentoListSerializer,
    PublicRequisitoSerializer,
    RequisitoRecuperacionSerializer,
)


class DocumentoMixin:
    """Comportamiento compartido: filtrar por profesor dueño (PROFESOR)
    o devolver todos (ADMIN), asignar profesor y periodo automáticamente al crear.

    Cada ViewSet declara `recurso_activo` (Periodo.Recurso.*) para indicar de
    qué tipo de recurso es el documento; al crear, el periodo se toma del
    Periodo con el flag correspondiente activado, y al listar para el profesor
    solo se devuelven los documentos cuyo periodo tenga ese flag activo
    (los documentos de trimestres pasados quedan ocultos para el profesor,
    pero siguen disponibles para el admin).
    """

    recurso_activo = None  # Sobrescrito por cada ViewSet concreto.

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.es_profesor:
            try:
                qs = qs.filter(profesor=user.perfil_profesor)
            except Exception:
                return qs.none()
            # Solo periodos activos para este recurso (trimestres pasados ocultos).
            field = Periodo._RECURSO_FIELD.get(self.recurso_activo) if self.recurso_activo else None
            if field:
                qs = qs.filter(**{f"periodo__{field}": True})
            return qs
        return qs  # ADMIN ve todo

    def _resolver_periodo(self):
        """Periodo activo para el recurso de este viewset. None si no hay."""
        if not self.recurso_activo:
            return None
        return Periodo.get_activo(self.recurso_activo)

    def perform_create(self, serializer):
        user = self.request.user
        periodo = self._resolver_periodo()
        if periodo is None:
            raise ValidationError({
                "periodo": [
                    "No hay un periodo activo para este tipo de documento. "
                    "Pide al administrador que marque un periodo como activo."
                ]
            })
        try:
            extra = {"periodo": periodo}
            if user.es_profesor:
                perfil = user.perfil_profesor
                extra["profesor"] = perfil
                # Snapshot: si más adelante eliminan al profesor, el
                # documento conserva su nombre y correo para el historial.
                extra["profesor_nombre"] = perfil.nombre_completo or ""
                extra["profesor_correo"] = perfil.correo_institucional or ""
            serializer.save(**extra)
        except IntegrityError:
            raise ValidationError(
                {"non_field_errors": ["Ya existe un documento para este profesor, periodo, UEA y grupo."]}
            )

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.puede_eliminar():
            return Response(
                {"success": False, "errors": {"estado": "Solo se pueden eliminar documentos en estado BORRADOR."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado(self, request, pk=None):
        """POST …/{id}/cambiar-estado/ con body {"estado": "PUBLICADO|BORRADOR"}."""
        obj = self.get_object()
        nuevo = request.data.get("estado")
        estados_validos = [e.value for e in obj.Estado]
        if nuevo not in estados_validos:
            return Response(
                {"success": False, "errors": {"estado": f"Estado inválido. Opciones: {estados_validos}"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.estado = nuevo
        obj.save(update_fields=["estado"])
        return Response({"success": True, "estado": obj.estado})


class CartaTematicaViewSet(DocumentoMixin, viewsets.ModelViewSet):
    queryset = CartaTematica.objects.select_related(
        "profesor", "uea", "periodo"
    ).all()
    serializer_class = CartaTematicaSerializer
    permission_classes = [IsAuthenticated, IsOwnerProfesorOrAdminReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "periodo", "uea"]
    search_fields = ["nombre_grupo", "id_grupo", "uea__nombre"]
    ordering_fields = ["created_at", "updated_at", "estado"]
    recurso_activo = Periodo.Recurso.CARTAS


class RequisitoRecuperacionViewSet(DocumentoMixin, viewsets.ModelViewSet):
    queryset = RequisitoRecuperacion.objects.select_related(
        "profesor", "uea", "periodo"
    ).all()
    serializer_class = RequisitoRecuperacionSerializer
    permission_classes = [IsAuthenticated, IsOwnerProfesorOrAdminReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "periodo", "uea"]
    search_fields = ["nombre_grupo", "id_grupo", "uea__nombre"]
    ordering_fields = ["created_at", "updated_at", "estado"]
    recurso_activo = Periodo.Recurso.REQUISITOS


# ---------------------------------------------------------------------------
# Vista pública (sin auth)
# ---------------------------------------------------------------------------

class PublicCartaView(generics.RetrieveAPIView):
    """GET /api/v1/publico/cartas/{id}/ — Sin auth, solo cartas PUBLICADAS.

    Devuelve los datos visibles en la página pública. Las cartas en BORRADOR
    o ENVIADO no aparecen aquí (regresa 404).
    """

    queryset = (
        CartaTematica.objects
        .filter(estado=CartaTematica.Estado.PUBLICADO)
        .select_related("profesor", "uea__licenciatura", "periodo")
    )
    serializer_class = PublicCartaTematicaSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # No procesar JWT (no requerido)


class PublicRequisitoView(generics.RetrieveAPIView):
    """GET /api/v1/publico/requisitos/{id}/ — Sin auth, solo requisitos PUBLICADOS."""

    queryset = (
        RequisitoRecuperacion.objects
        .filter(estado=RequisitoRecuperacion.Estado.PUBLICADO)
        .select_related("profesor", "uea__licenciatura", "periodo")
    )
    serializer_class = PublicRequisitoSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


# ---------------------------------------------------------------------------
# Listados públicos (para el explorador de la página principal)
# ---------------------------------------------------------------------------

class _PublicListBase(generics.ListAPIView):
    """Base para listados públicos de documentos PUBLICADOS, sin auth.

    Acepta filtros ?licenciatura= y ?uea= por query params.
    """

    serializer_class = PublicDocumentoListSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "nombre_grupo"]
    ordering = ["-created_at"]

    pagination_class = None  # respuesta plana — el front filtra/ordena en cliente

    model = None  # subclase

    def get_queryset(self):
        qs = (
            self.model.objects
            .filter(estado=self.model.Estado.PUBLICADO)
            .select_related("profesor", "uea", "periodo")
        )
        params = self.request.query_params
        licenciatura = params.get("licenciatura")
        uea = params.get("uea")
        if licenciatura:
            qs = qs.filter(uea__licenciatura_id=licenciatura)
        if uea:
            qs = qs.filter(uea_id=uea)
        return qs


class PublicCartaListView(_PublicListBase):
    """GET /api/v1/publico/cartas/?licenciatura=&uea= — sin auth."""
    model = CartaTematica


class PublicRequisitoListView(_PublicListBase):
    """GET /api/v1/publico/requisitos/?licenciatura=&uea= — sin auth."""
    model = RequisitoRecuperacion
