"""ViewSets del módulo Autoevaluación."""

from decimal import Decimal

from django.db import IntegrityError
from django.db.models import ProtectedError, Q
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsAdmin, IsProfesor

from .models import Formulario, NivelDesempeno, Pregunta, Respuesta, Seccion
from .serializers import (
    FormularioDisponibleSerializer,
    FormularioListSerializer,
    FormularioSerializer,
    NivelDesempenoSerializer,
    PreguntaSerializer,
    RespuestaSerializer,
    SeccionSerializer,
)


# ---------------------------------------------------------------------------
# Helpers de cálculo de puntaje
# ---------------------------------------------------------------------------


def _calcular_puntaje(respuesta: Respuesta):
    """Calcula (puntaje_obtenido, puntaje_maximo) para una respuesta.

    Reglas por tipo de pregunta:
        TEXTO_CORTO / TEXTO_LARGO  → no puntable (se ignora)
        OPCION_UNICA               → puntos de la opción seleccionada
                                     máx = opción de mayor puntaje
        CASILLAS                   → suma de puntos de todas las seleccionadas
                                     máx = suma de opciones con puntos > 0
        LISTA_DESPLEGABLE          → igual que OPCION_UNICA
        ESCALA_LINEAL              → valor × config.puntos_factor
                                     máx = config.max × puntos_factor
        SI_NO                      → config.puntos_si o config.puntos_no
                                     máx = max(puntos_si, puntos_no)
    """
    obtenido = Decimal("0")
    maximo = Decimal("0")

    items = list(
        respuesta.items.select_related("pregunta")
        .prefetch_related(
            "opciones_seleccionadas",
            "pregunta__opciones",
            "pregunta__filas",
            "celdas__opcion",
        )
    )

    for item in items:
        pregunta = item.pregunta
        tipo = pregunta.tipo

        if tipo in Pregunta.TIPOS_NO_PUNTABLES:
            continue

        if tipo == Pregunta.Tipo.CUADRICULA:
            all_opts = list(pregunta.opciones.all())
            filas = list(pregunta.filas.all())
            if all_opts and filas:
                maximo += max(op.puntos for op in all_opts) * len(filas)
            for celda in item.celdas.all():
                obtenido += celda.opcion.puntos
            continue

        if tipo == Pregunta.Tipo.ESCALA_LINEAL:
            cfg = pregunta.config or {}
            factor = Decimal(str(cfg.get("puntos_factor", 1)))
            max_val = Decimal(str(cfg.get("max", 5)))
            maximo += max_val * factor
            if item.valor_texto:
                try:
                    obtenido += Decimal(item.valor_texto) * factor
                except Exception:
                    pass

        elif tipo == Pregunta.Tipo.SI_NO:
            cfg = pregunta.config or {}
            pts_si = Decimal(str(cfg.get("puntos_si", 1)))
            pts_no = Decimal(str(cfg.get("puntos_no", 0)))
            maximo += max(pts_si, pts_no)
            if item.valor_texto == "SI":
                obtenido += pts_si
            elif item.valor_texto == "NO":
                obtenido += pts_no

        else:  # OPCION_UNICA, CASILLAS, LISTA_DESPLEGABLE
            all_opts = list(pregunta.opciones.all())
            positive_opts = [op for op in all_opts if op.puntos > 0]

            if tipo == Pregunta.Tipo.CASILLAS:
                maximo += sum(op.puntos for op in positive_opts)
            else:
                maximo += max((op.puntos for op in all_opts), default=Decimal("0"))

            for opcion in item.opciones_seleccionadas.all():
                obtenido += opcion.puntos

    return obtenido, maximo


def _asignar_nivel(formulario: Formulario, porcentaje: Decimal):
    """Busca el NivelDesempeno cuyo rango incluye el porcentaje obtenido."""
    return formulario.niveles.filter(
        porcentaje_min__lte=porcentaje,
        porcentaje_max__gte=porcentaje,
    ).order_by("porcentaje_min").first()


# ---------------------------------------------------------------------------
# Admin — Formulario
# ---------------------------------------------------------------------------


class FormularioViewSet(viewsets.ModelViewSet):
    """CRUD de formularios + acciones publicar/cerrar/publicar_revision/estadísticas (ADMIN)."""

    queryset = Formulario.objects.select_related("periodo").prefetch_related(
        "secciones__preguntas__opciones",
        "secciones__preguntas__filas",
        "preguntas__opciones",
        "preguntas__filas",
        "niveles",
    )
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "periodo"]
    search_fields = ["titulo"]
    ordering_fields = ["created_at", "estado"]

    def get_serializer_class(self):
        if self.action == "list":
            return FormularioListSerializer
        return FormularioSerializer

    def _validar_periodo_habilitado(self, periodo):
        """Solo se permite crear/mover formularios a periodos habilitados para autoevaluación."""
        if periodo is None or not (periodo.estado and periodo.activo_autoevaluacion):
            raise ValidationError({
                "periodo": [
                    "El periodo seleccionado no está habilitado para autoevaluaciones."
                ]
            })

    def perform_create(self, serializer):
        self._validar_periodo_habilitado(serializer.validated_data.get("periodo"))
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        periodo = serializer.validated_data.get("periodo", serializer.instance.periodo)
        self._validar_periodo_habilitado(periodo)
        serializer.save()

    def perform_destroy(self, instance):
        """Borra el formulario y sus respuestas en cascada.

        Las respuestas usan on_delete=PROTECT para preservar el historial,
        así que aquí las eliminamos explícitamente antes del formulario.
        Si la operación falla por integridad referencial, devolvemos un
        mensaje claro en lugar de un 500.
        """
        try:
            # Las respuestas se borran en cascada via items;
            # Pregunta y Seccion ya son CASCADE.
            instance.respuestas.all().delete()
            instance.delete()
        except ProtectedError as exc:
            raise ValidationError({
                "detail": (
                    "No se puede eliminar este formulario porque tiene "
                    "registros dependientes protegidos. "
                    f"({exc})"
                )
            })

    @action(detail=True, methods=["post"])
    def publicar(self, request, pk=None):
        formulario = self.get_object()
        try:
            formulario.publicar()
        except ValueError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]})
        return Response({"success": True, "estado": formulario.estado, "version": formulario.version})

    @action(detail=True, methods=["post"])
    def cerrar(self, request, pk=None):
        formulario = self.get_object()
        try:
            formulario.cerrar()
        except ValueError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]})
        return Response({"success": True, "estado": formulario.estado})

    @action(detail=True, methods=["post"])
    def despublicar(self, request, pk=None):
        """PUBLICADO o CERRADO → BORRADOR para reabrir edición."""
        formulario = self.get_object()
        try:
            formulario.despublicar()
        except ValueError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]})
        return Response({"success": True, "estado": formulario.estado})

    @action(detail=True, methods=["post"])
    def reabrir(self, request, pk=None):
        """CERRADO → PUBLICADO sin incrementar versión.

        Permite volver a aceptar respuestas si se cerró antes de tiempo.
        Las respuestas previamente enviadas no se ven afectadas.
        """
        formulario = self.get_object()
        try:
            formulario.reabrir()
        except ValueError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]})
        return Response({"success": True, "estado": formulario.estado})

    @action(detail=True, methods=["post"], url_path="publicar-revision")
    def publicar_revision(self, request, pk=None):
        """Incrementa la versión del formulario y lo vuelve a publicar (desde CERRADO).

        Todos los profesores verán el formulario como pendiente, incluso si ya
        respondieron la versión anterior. Las respuestas anteriores se conservan.
        """
        formulario = self.get_object()
        try:
            formulario.publicar_revision()
        except ValueError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]})
        return Response({
            "success": True,
            "estado": formulario.estado,
            "version": formulario.version,
        })

    @action(detail=True, methods=["get"])
    def respuestas(self, request, pk=None):
        """Lista las respuestas enviadas a la versión actual del formulario."""
        formulario = self.get_object()
        version = request.query_params.get("version", formulario.version)
        qs = formulario.respuestas.filter(
            estado=Respuesta.Estado.ENVIADO,
            version_formulario=version,
        ).select_related("profesor", "nivel_desempeno")
        serializer = RespuestaSerializer(qs, many=True, context={"request": request})
        return Response({"count": qs.count(), "version": version, "results": serializer.data})

    @action(detail=True, methods=["get"])
    def estadisticas(self, request, pk=None):
        """Estadísticas agregadas por pregunta + distribución de niveles."""
        formulario = self.get_object()
        version = request.query_params.get("version", formulario.version)
        preguntas = formulario.preguntas.prefetch_related("opciones")
        enviadas = formulario.respuestas.filter(
            estado=Respuesta.Estado.ENVIADO,
            version_formulario=version,
        )
        total_enviadas = enviadas.count()

        # — Estadísticas por pregunta —
        resultados = []
        for pregunta in preguntas:
            items_qs = pregunta.respuestas_recibidas.filter(
                respuesta__estado=Respuesta.Estado.ENVIADO,
                respuesta__version_formulario=version,
            )
            total_resp = items_qs.count()

            opciones_stats = []
            if pregunta.tiene_opciones():
                for opcion in pregunta.opciones.all():
                    conteo = opcion.selecciones.filter(
                        respuesta__estado=Respuesta.Estado.ENVIADO,
                        respuesta__version_formulario=version,
                    ).count()
                    opciones_stats.append({
                        "opcion_id": opcion.id,
                        "texto": opcion.texto,
                        "puntos": float(opcion.puntos),
                        "conteo": conteo,
                    })

            promedio = None
            if pregunta.tipo == Pregunta.Tipo.ESCALA_LINEAL:
                valores = []
                for item in items_qs:
                    try:
                        valores.append(float(item.valor_texto))
                    except (ValueError, TypeError):
                        pass
                if valores:
                    promedio = round(sum(valores) / len(valores), 2)

            resultados.append({
                "pregunta_id": pregunta.id,
                "texto": pregunta.texto,
                "tipo": pregunta.tipo,
                "puntable": pregunta.es_puntable(),
                "total_respuestas": total_resp,
                "opciones": opciones_stats,
                "promedio": promedio,
            })

        # — Distribución de niveles de desempeño —
        distribucion_niveles = []
        for nivel in formulario.niveles.all():
            count = enviadas.filter(nivel_desempeno=nivel).count()
            distribucion_niveles.append({
                "nivel_id": nivel.id,
                "nombre": nivel.nombre,
                "color": nivel.color,
                "porcentaje_min": float(nivel.porcentaje_min),
                "porcentaje_max": float(nivel.porcentaje_max),
                "count": count,
            })
        sin_nivel = enviadas.filter(nivel_desempeno__isnull=True).count()

        # — Promedio general de puntaje —
        puntajes = list(enviadas.filter(
            porcentaje__isnull=False
        ).values_list("porcentaje", flat=True))
        promedio_general = (
            round(sum(float(p) for p in puntajes) / len(puntajes), 2)
            if puntajes else None
        )

        return Response({
            "formulario_id": formulario.id,
            "titulo": formulario.titulo,
            "version": int(version),
            "total_respuestas_enviadas": total_enviadas,
            "promedio_porcentaje": promedio_general,
            "distribucion_niveles": distribucion_niveles,
            "sin_nivel_asignado": sin_nivel,
            "preguntas": resultados,
        })


# ---------------------------------------------------------------------------
# Admin — Sección
# ---------------------------------------------------------------------------


class SeccionViewSet(viewsets.ModelViewSet):
    """CRUD de secciones de un formulario (solo ADMIN)."""

    queryset = Seccion.objects.select_related("formulario").prefetch_related(
        "preguntas__opciones"
    )
    serializer_class = SeccionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["formulario"]

    def _check_formulario_editable(self, formulario):
        if formulario.estado != Formulario.Estado.BORRADOR:
            raise ValidationError({
                "non_field_errors": [
                    f"No se puede modificar la estructura de un formulario {formulario.estado}. "
                    "Cierre el formulario primero para volver a BORRADOR."
                ]
            })

    def perform_update(self, serializer):
        self._check_formulario_editable(serializer.instance.formulario)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_formulario_editable(instance.formulario)
        instance.delete()


# ---------------------------------------------------------------------------
# Admin — Pregunta
# ---------------------------------------------------------------------------


class PreguntaViewSet(viewsets.ModelViewSet):
    """CRUD de preguntas (solo ADMIN)."""

    queryset = Pregunta.objects.select_related("formulario", "seccion").prefetch_related(
        "opciones"
    )
    serializer_class = PreguntaSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["formulario", "seccion", "tipo", "obligatoria"]
    ordering_fields = ["orden"]

    def _check_formulario_editable(self, formulario):
        if formulario.estado != Formulario.Estado.BORRADOR:
            raise ValidationError({
                "non_field_errors": [
                    f"No se puede modificar preguntas de un formulario {formulario.estado}. "
                    "Cierre el formulario primero para volver a BORRADOR."
                ]
            })

    def perform_update(self, serializer):
        self._check_formulario_editable(serializer.instance.formulario)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_formulario_editable(instance.formulario)
        instance.delete()


# ---------------------------------------------------------------------------
# Admin — Nivel de Desempeño
# ---------------------------------------------------------------------------


class NivelDesempenoViewSet(viewsets.ModelViewSet):
    """CRUD de niveles de desempeño por formulario (solo ADMIN)."""

    queryset = NivelDesempeno.objects.select_related("formulario")
    serializer_class = NivelDesempenoSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["formulario"]


# ---------------------------------------------------------------------------
# Profesor — Formularios disponibles
# ---------------------------------------------------------------------------


class FormulariosDisponiblesViewSet(viewsets.ReadOnlyModelViewSet):
    """Formularios visibles para el profesor autenticado.

    Incluye PUBLICADO y CERRADO:
      - PUBLICADO: puede responder.
      - CERRADO: ya no se aceptan respuestas nuevas, pero quienes ya
                 enviaron pueden seguir consultando su resultado.
        El endpoint /respuestas/ rechaza envíos si estado != PUBLICADO.
    """

    serializer_class = FormularioDisponibleSerializer
    permission_classes = [IsAuthenticated, IsProfesor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["periodo"]

    def get_queryset(self):
        # Visibles para el profesor:
        #   (a) Formularios PUBLICADO/CERRADO cuyo periodo está activo para AE.
        #   (b) Formularios donde el profesor ya tiene una Respuesta — aunque
        #       el periodo del formulario ya esté cerrado (consulta histórica).
        base = Formulario.objects.filter(
            estado__in=[
                Formulario.Estado.PUBLICADO,
                Formulario.Estado.CERRADO,
            ],
        )
        user = self.request.user
        try:
            profesor = user.perfil_profesor
        except Exception:
            profesor = None
        abiertos = Q(periodo__activo_autoevaluacion=True, periodo__estado=True)
        if profesor is not None:
            historial = Q(respuestas__profesor=profesor)
            base = base.filter(abiertos | historial)
        else:
            base = base.filter(abiertos)
        return (
            base.distinct()
            .select_related("periodo")
            .prefetch_related(
                "secciones__preguntas__opciones",
                "secciones__preguntas__filas",
                "preguntas__opciones",
                "preguntas__filas",
                "niveles",
            )
        )


# ---------------------------------------------------------------------------
# Profesor — Respuestas
# ---------------------------------------------------------------------------


class RespuestaViewSet(viewsets.ModelViewSet):
    """Respuestas del profesor autenticado a formularios."""

    serializer_class = RespuestaSerializer
    permission_classes = [IsAuthenticated, IsProfesor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["formulario", "estado"]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        try:
            return (
                Respuesta.objects.filter(profesor=user.perfil_profesor)
                .select_related("formulario", "profesor", "nivel_desempeno")
                .prefetch_related(
                    "items__opciones_seleccionadas",
                    "items__celdas__opcion",
                )
            )
        except Exception:
            return Respuesta.objects.none()

    def _bloqueo_periodo(self):
        return ValidationError({
            "periodo": [
                "La autoevaluación de este periodo ya no está abierta."
            ]
        })

    def _periodo_abierto(self, formulario):
        p = getattr(formulario, "periodo", None)
        return bool(p and p.estado and p.activo_autoevaluacion)

    def perform_create(self, serializer):
        formulario = serializer.validated_data["formulario"]
        if not self._periodo_abierto(formulario):
            raise self._bloqueo_periodo()
        try:
            serializer.save(
                profesor=self.request.user.perfil_profesor,
                version_formulario=formulario.version,
            )
        except IntegrityError:
            raise ValidationError({
                "non_field_errors": [
                    "Ya existe una respuesta para esta versión del formulario."
                ]
            })

    def perform_update(self, serializer):
        formulario = serializer.instance.formulario
        if not self._periodo_abierto(formulario):
            raise self._bloqueo_periodo()
        serializer.save()

    @action(detail=True, methods=["post"])
    def enviar(self, request, pk=None):
        """Valida preguntas obligatorias, calcula puntaje y marca la respuesta como ENVIADO."""
        respuesta = self.get_object()

        if respuesta.estado == Respuesta.Estado.ENVIADO:
            raise ValidationError({"non_field_errors": ["La respuesta ya fue enviada."]})

        if not self._periodo_abierto(respuesta.formulario):
            raise self._bloqueo_periodo()

        # — Validar preguntas obligatorias —
        preguntas_obligatorias = respuesta.formulario.preguntas.filter(obligatoria=True)
        preguntas_respondidas_ids = set(
            respuesta.items.values_list("pregunta_id", flat=True)
        )

        faltantes = []
        for pregunta in preguntas_obligatorias:
            if pregunta.id not in preguntas_respondidas_ids:
                faltantes.append(pregunta.id)
                continue
            item = respuesta.items.get(pregunta=pregunta)
            if pregunta.es_cuadricula():
                if item.celdas.count() < pregunta.filas.count():
                    faltantes.append(pregunta.id)
            elif pregunta.tiene_opciones():
                if not item.opciones_seleccionadas.exists():
                    faltantes.append(pregunta.id)
            elif pregunta.tipo == Pregunta.Tipo.SI_NO:
                if not item.valor_texto.strip():
                    faltantes.append(pregunta.id)
            elif not item.valor_texto.strip():
                faltantes.append(pregunta.id)

        if faltantes:
            raise ValidationError({
                "preguntas_faltantes": faltantes,
                "detail": "Hay preguntas obligatorias sin responder.",
            })

        # — Calcular puntaje —
        obtenido, maximo = _calcular_puntaje(respuesta)
        porcentaje = (
            round(obtenido / maximo * Decimal("100"), 2)
            if maximo > 0
            else Decimal("0")
        )
        nivel = _asignar_nivel(respuesta.formulario, porcentaje)

        # — Persistir —
        respuesta.estado = Respuesta.Estado.ENVIADO
        respuesta.enviado_at = timezone.now()
        respuesta.puntaje_obtenido = obtenido
        respuesta.puntaje_maximo = maximo
        respuesta.porcentaje = porcentaje
        respuesta.nivel_desempeno = nivel
        respuesta.save(update_fields=[
            "estado", "enviado_at",
            "puntaje_obtenido", "puntaje_maximo", "porcentaje",
            "nivel_desempeno",
        ])

        serializer = self.get_serializer(respuesta)
        return Response(serializer.data)
