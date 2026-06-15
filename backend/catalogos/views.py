"""ViewSets de catálogos institucionales."""

import csv
import io

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsAdmin, IsAdminOrReadOnly

from .models import Area, Departamento, Licenciatura, Periodo, Posgrado, UEA
from .serializers import (
    AreaSerializer,
    DepartamentoSerializer,
    LicenciaturaSerializer,
    PeriodoSerializer,
    PosgradoSerializer,
    UEASerializer,
)


class DepartamentoViewSet(viewsets.ModelViewSet):
    """Lectura para todos los autenticados; escritura solo ADMIN."""

    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["estado"]
    search_fields = ["clave", "nombre"]


class LicenciaturaViewSet(viewsets.ModelViewSet):
    queryset = Licenciatura.objects.select_related("departamento").all()
    serializer_class = LicenciaturaSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["estado", "departamento"]
    search_fields = ["clave", "nombre"]


class PosgradoViewSet(viewsets.ModelViewSet):
    queryset = Posgrado.objects.select_related("departamento").all()
    serializer_class = PosgradoSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["estado", "departamento"]
    search_fields = ["clave", "nombre"]


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["estado"]
    search_fields = ["nombre", "descripcion"]


class UEAViewSet(viewsets.ModelViewSet):
    queryset = UEA.objects.select_related("licenciatura", "posgrado", "area").all()
    serializer_class = UEASerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "licenciatura", "posgrado", "area", "tipo", "trimestre"]
    search_fields = ["clave", "nombre"]
    ordering_fields = ["trimestre", "nombre", "clave"]

    @action(detail=False, methods=["post"], permission_classes=[IsAdmin],
            url_path="import-csv")
    def import_csv(self, request):
        """POST /api/v1/uea/import-csv/ — Importa UEA desde un archivo CSV.

        Columnas esperadas (con encabezado):
            clave, nombre, programa_clave, trimestre, tipo, creditos,
            area_nombre, area_descripcion, url

        Obligatorias: clave, nombre, programa_clave.
        `programa_clave` acepta la clave de una Licenciatura o de un Posgrado;
        el sistema detecta a cuál pertenece. Si una misma clave existe en
        ambas tablas la fila se rechaza como ambigua.
        """
        archivo = request.FILES.get("file")
        if not archivo:
            return Response(
                {"success": False, "errors": {"file": "Se requiere el archivo CSV."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        decoded = archivo.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))

        fieldnames = set(reader.fieldnames or [])
        required_cols = {"clave", "nombre", "programa_clave"}
        faltantes = required_cols - fieldnames
        if faltantes:
            return Response(
                {
                    "success": False,
                    "errors": {
                        "file": (
                            "El CSV debe tener las columnas clave, nombre y "
                            f"programa_clave. Faltan: {', '.join(sorted(faltantes))}."
                        )
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created, updated, errors = 0, 0, []
        lic_cache = {l.clave: l for l in Licenciatura.objects.all()}
        pos_cache = {p.clave: p for p in Posgrado.objects.all()}
        area_cache = {(a.nombre, a.descripcion): a for a in Area.objects.all()}
        colisiones = set(lic_cache) & set(pos_cache)

        for i, row in enumerate(reader, start=2):
            clave = row.get("clave", "").strip()
            nombre = row.get("nombre", "").strip()

            if not (clave and nombre):
                errors.append(f"Fila {i}: clave y nombre son obligatorios.")
                continue

            programa_clave = (row.get("programa_clave") or "").strip()
            if not programa_clave:
                errors.append(f"Fila {i}: programa_clave es obligatoria.")
                continue
            if programa_clave in colisiones:
                errors.append(
                    f"Fila {i}: clave '{programa_clave}' es ambigua "
                    "(existe en Licenciatura y Posgrado)."
                )
                continue

            licenciatura = lic_cache.get(programa_clave)
            posgrado = None if licenciatura else pos_cache.get(programa_clave)
            if not licenciatura and not posgrado:
                errors.append(
                    f"Fila {i}: programa_clave '{programa_clave}' no corresponde "
                    "a ninguna Licenciatura ni Posgrado."
                )
                continue

            # Área opcional: si trae nombre, hace upsert por (nombre, descripcion).
            area_nombre = row.get("area_nombre", "").strip()
            area_desc = row.get("area_descripcion", "").strip()
            area_obj = None
            if area_nombre:
                key = (area_nombre, area_desc)
                area_obj = area_cache.get(key)
                if area_obj is None:
                    area_obj, _ = Area.objects.get_or_create(
                        nombre=area_nombre,
                        descripcion=area_desc,
                        defaults={"estado": True},
                    )
                    area_cache[key] = area_obj

            creditos_raw = (row.get("creditos") or "").strip()
            try:
                creditos = int(creditos_raw) if creditos_raw else None
            except ValueError:
                creditos = None

            defaults = {
                "nombre": nombre,
                "licenciatura": licenciatura,
                "posgrado": posgrado,
                "area": area_obj,
                "trimestre": (row.get("trimestre") or "").strip(),
                "tipo": (row.get("tipo") or UEA.Tipo.OBLIGATORIA).strip(),
                "creditos": creditos,
                "liga": (row.get("url") or "").strip(),
                "estado": True,
            }

            obj, was_created = UEA.objects.update_or_create(clave=clave, defaults=defaults)
            if was_created:
                created += 1
            else:
                updated += 1

        return Response(
            {
                "success": True,
                "created": created,
                "updated": updated,
                "errors": errors,
                "total_rows": created + updated + len(errors),
            },
            status=status.HTTP_200_OK,
        )


class PublicLicenciaturaListView(generics.ListAPIView):
    """GET /api/v1/publico/licenciaturas/ — Sin auth.

    Lista licenciaturas activas, usado por la home pública para el selector.
    """
    serializer_class = LicenciaturaSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = None

    def get_queryset(self):
        return Licenciatura.objects.filter(estado=True).select_related("departamento").order_by("nombre")


class PublicUEAListView(generics.ListAPIView):
    """GET /api/v1/publico/uea/?licenciatura=ID — Sin auth.

    Lista UEAs activas, opcionalmente filtradas por licenciatura.
    """
    serializer_class = UEASerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = None

    def get_queryset(self):
        qs = (
            UEA.objects.filter(estado=True)
            .select_related("licenciatura", "posgrado", "area")
            .order_by("clave")
        )
        lic = self.request.query_params.get("licenciatura")
        if lic:
            qs = qs.filter(licenciatura_id=lic)
        pos = self.request.query_params.get("posgrado")
        if pos:
            qs = qs.filter(posgrado_id=pos)
        return qs


class PeriodoViewSet(viewsets.ModelViewSet):
    queryset = Periodo.objects.all()
    serializer_class = PeriodoSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "activo", "estado",
        "activo_cartas", "activo_requisitos", "activo_autoevaluacion",
    ]

    def _is_activo_para_algun_recurso(self, periodo):
        return any([
            periodo.activo_cartas,
            periodo.activo_requisitos,
            periodo.activo_autoevaluacion,
        ])

    def _conteo_dependencias(self, periodo):
        """Conteo de documentos y respuestas asociadas al periodo (para preview)."""
        # Import local para evitar ciclos.
        from autoevaluacion.models import Formulario, Respuesta
        from documentos.models import CartaTematica, RequisitoRecuperacion

        cartas = CartaTematica.objects.filter(periodo=periodo).count()
        requisitos = RequisitoRecuperacion.objects.filter(periodo=periodo).count()
        formularios = Formulario.objects.filter(periodo=periodo).count()
        respuestas = Respuesta.objects.filter(formulario__periodo=periodo).count()
        return {
            "cartas_tematicas": cartas,
            "requisitos_recuperacion": requisitos,
            "formularios_autoevaluacion": formularios,
            "respuestas_autoevaluacion": respuestas,
        }

    @action(detail=True, methods=["get"], url_path="preview-eliminacion")
    def preview_eliminacion(self, request, pk=None):
        """GET /api/v1/periodos/{id}/preview-eliminacion/

        Devuelve si el periodo se puede eliminar y cuántos documentos/respuestas
        se borrarán en cascada si lo es. Pensado para que el frontend muestre
        un diálogo de confirmación informado.
        """
        periodo = self.get_object()
        activo = self._is_activo_para_algun_recurso(periodo)
        return Response({
            "periodo": {"id": periodo.id, "clave": periodo.clave},
            "puede_eliminar": not activo,
            "razon_bloqueo": (
                "El periodo está activo para al menos un recurso. "
                "Desactívalo antes de eliminarlo."
            ) if activo else None,
            "dependencias": self._conteo_dependencias(periodo),
        })

    def perform_destroy(self, instance):
        """Elimina el periodo y todos sus documentos/formularios/respuestas en cascada.

        Bloquea la operación si el periodo sigue activo para algún recurso.
        Las relaciones a Periodo son PROTECT, así que el borrado se hace
        explícitamente en orden seguro dentro de una transacción.
        """
        if self._is_activo_para_algun_recurso(instance):
            raise ValidationError({
                "detail": (
                    "No se puede eliminar el periodo "
                    f"'{instance.clave}' porque está activo para al menos un "
                    "recurso (Cartas, Requisitos o Autoevaluación). "
                    "Desactívalo primero."
                )
            })

        from autoevaluacion.models import Formulario, Respuesta
        from documentos.models import CartaTematica, RequisitoRecuperacion

        with transaction.atomic():
            # Orden inverso a las dependencias PROTECT:
            # 1) Respuestas (PROTECTed por Formulario)
            Respuesta.objects.filter(formulario__periodo=instance).delete()
            # 2) Formularios (PROTECTed por Periodo) — Secciones/Preguntas
            #    bajan en cascada porque sus FK son CASCADE.
            Formulario.objects.filter(periodo=instance).delete()
            # 3) Documentos del profesor (PROTECTed por Periodo)
            CartaTematica.objects.filter(periodo=instance).delete()
            RequisitoRecuperacion.objects.filter(periodo=instance).delete()
            # 4) Finalmente el periodo
            instance.delete()

    @action(detail=False, methods=["get"], url_path="activos")
    def activos(self, request):
        """GET /api/v1/periodos/activos/

        Devuelve el periodo activo para cada tipo de recurso, o null si no hay.
        Pensado para que el frontend pre-seleccione el periodo correcto al
        crear cada tipo de documento.
        """
        def _serializar(p):
            if not p:
                return None
            return {
                "id": p.id,
                "clave": p.clave,
                "fecha_inicio": p.fecha_inicio,
                "fecha_fin": p.fecha_fin,
            }

        return Response({
            "cartas": _serializar(Periodo.get_activo(Periodo.Recurso.CARTAS)),
            "requisitos": _serializar(Periodo.get_activo(Periodo.Recurso.REQUISITOS)),
            "autoevaluacion": _serializar(
                Periodo.get_activo(Periodo.Recurso.AUTOEVALUACION)
            ),
        })
