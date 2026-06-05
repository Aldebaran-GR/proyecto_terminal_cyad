"""ViewSets de documentos académicos con reglas de propiedad y estado."""

from django.db import IntegrityError

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsOwnerProfesorOrAdminReadOnly

from .models import CartaTematica, RequisitoRecuperacion
from .serializers import CartaTematicaSerializer, RequisitoRecuperacionSerializer


class DocumentoMixin:
    """Comportamiento compartido: filtrar por profesor dueño (PROFESOR)
    o devolver todos (ADMIN), y asignar profesor automáticamente al crear."""

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.es_profesor:
            try:
                return qs.filter(profesor=user.perfil_profesor)
            except Exception:
                return qs.none()
        return qs  # ADMIN ve todo

    def perform_create(self, serializer):
        user = self.request.user
        try:
            if user.es_profesor:
                serializer.save(profesor=user.perfil_profesor)
            else:
                serializer.save()
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
        """POST …/{id}/cambiar-estado/ con body {"estado": "PUBLICADO|ENVIADO|BORRADOR"}."""
        obj = self.get_object()
        nuevo = request.data.get("estado")
        estados_validos = [e.value for e in obj.Estado]
        if nuevo not in estados_validos:
            return Response(
                {"success": False, "errors": {"estado": f"Estado inválido. Opciones: {estados_validos}"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if obj.estado == obj.Estado.ENVIADO and not request.user.es_admin:
            return Response(
                {"success": False, "errors": {"estado": "Un documento ENVIADO no puede cambiar de estado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.estado = nuevo
        obj.save(update_fields=["estado"])
        return Response({"success": True, "estado": obj.estado})


class CartaTematicaViewSet(DocumentoMixin, viewsets.ModelViewSet):
    queryset = CartaTematica.objects.select_related(
        "profesor", "uea", "periodo"
    ).prefetch_related("temas__subtemas", "bibliografias", "criterios").all()
    serializer_class = CartaTematicaSerializer
    permission_classes = [IsAuthenticated, IsOwnerProfesorOrAdminReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "periodo", "uea"]
    search_fields = ["nombre_grupo", "id_grupo", "uea__nombre"]
    ordering_fields = ["created_at", "updated_at", "estado"]


class RequisitoRecuperacionViewSet(DocumentoMixin, viewsets.ModelViewSet):
    queryset = RequisitoRecuperacion.objects.select_related(
        "profesor", "uea", "periodo"
    ).prefetch_related("items").all()
    serializer_class = RequisitoRecuperacionSerializer
    permission_classes = [IsAuthenticated, IsOwnerProfesorOrAdminReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "periodo", "uea"]
    search_fields = ["nombre_grupo", "id_grupo", "uea__nombre"]
    ordering_fields = ["created_at", "updated_at", "estado"]
