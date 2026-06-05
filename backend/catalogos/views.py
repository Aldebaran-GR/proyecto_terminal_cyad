"""ViewSets de catálogos institucionales."""

import csv
import io

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsAdmin, IsAdminOrReadOnly

from .models import Departamento, Licenciatura, Periodo, UEA
from .serializers import (
    DepartamentoSerializer,
    LicenciaturaSerializer,
    PeriodoSerializer,
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


class UEAViewSet(viewsets.ModelViewSet):
    queryset = UEA.objects.select_related("licenciatura").all()
    serializer_class = UEASerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "licenciatura", "tipo", "etapa", "trimestre"]
    search_fields = ["clave", "nombre"]
    ordering_fields = ["trimestre", "nombre", "clave"]

    @action(detail=False, methods=["post"], permission_classes=[IsAdmin],
            url_path="import-csv")
    def import_csv(self, request):
        """POST /api/v1/uea/import-csv/ — Importa UEA desde un archivo CSV.

        Columnas esperadas (con encabezado):
            clave, nombre, licenciatura_clave, trimestre, etapa, tipo, creditos
        """
        archivo = request.FILES.get("file")
        if not archivo:
            return Response(
                {"success": False, "errors": {"file": "Se requiere el archivo CSV."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        decoded = archivo.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))

        required_cols = {"clave", "nombre", "licenciatura_clave"}
        if not required_cols.issubset(set(reader.fieldnames or [])):
            return Response(
                {
                    "success": False,
                    "errors": {
                        "file": f"El CSV debe tener las columnas: {', '.join(required_cols)}"
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created, updated, errors = 0, 0, []
        lic_cache = {l.clave: l for l in Licenciatura.objects.all()}

        for i, row in enumerate(reader, start=2):
            clave = row.get("clave", "").strip()
            nombre = row.get("nombre", "").strip()
            lic_clave = row.get("licenciatura_clave", "").strip()

            if not (clave and nombre and lic_clave):
                errors.append(f"Fila {i}: clave, nombre y licenciatura_clave son obligatorios.")
                continue

            licenciatura = lic_cache.get(lic_clave)
            if not licenciatura:
                errors.append(f"Fila {i}: licenciatura_clave '{lic_clave}' no existe.")
                continue

            defaults = {
                "nombre": nombre,
                "licenciatura": licenciatura,
                "trimestre": row.get("trimestre") or None,
                "etapa": row.get("etapa", "").strip(),
                "tipo": row.get("tipo", UEA.Tipo.OBLIGATORIA).strip(),
                "creditos": row.get("creditos") or None,
                "estado": True,
            }
            # Normaliza trimestre y créditos a enteros si vienen como string
            for int_field in ("trimestre", "creditos"):
                val = defaults[int_field]
                if val is not None:
                    try:
                        defaults[int_field] = int(val)
                    except (ValueError, TypeError):
                        defaults[int_field] = None

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


class PeriodoViewSet(viewsets.ModelViewSet):
    queryset = Periodo.objects.all()
    serializer_class = PeriodoSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo", "estado"]
