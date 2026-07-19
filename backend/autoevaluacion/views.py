"""ViewSets del módulo Autoevaluación."""

from decimal import Decimal

from django.db import IntegrityError
from django.db.models import Avg, ProtectedError, Q
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsAdmin, IsProfesor

from django.db import transaction

from catalogos.models import Periodo

from .models import (
    FilaCuadricula,
    Formulario,
    NivelDesempeno,
    OpcionPregunta,
    Pregunta,
    Respuesta,
    RespuestaSeccion,
    Seccion,
)
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
    """Calcula puntaje ponderado por sección para una respuesta.

    Itera las secciones del formulario (en orden), acumula obtenido/maximo por
    sección y devuelve:
        {
          "secciones": [{"seccion_id", "peso", "obtenido", "maximo", "porcentaje"}],
          "porcentaje_ponderado": Decimal,   # Σ (% sección × peso / 100)
          "puntaje_obtenido_total": Decimal,
          "puntaje_maximo_total": Decimal,
        }

    Las preguntas sin sección no contribuyen al puntaje (no deben existir en
    formularios publicados por la validación de _validar_estructura_para_publicar).
    """
    items = list(
        respuesta.items.select_related("pregunta")
        .prefetch_related(
            "opciones_seleccionadas",
            "pregunta__opciones",
            "pregunta__filas",
            "celdas__opcion",
        )
    )
    item_by_pregunta = {item.pregunta_id: item for item in items}

    secciones = list(
        respuesta.formulario.secciones
        .prefetch_related("preguntas__opciones", "preguntas__filas")
        .order_by("orden")
    )

    resultado_secciones = []
    puntaje_obtenido_total = Decimal("0")
    puntaje_maximo_total = Decimal("0")

    for seccion in secciones:
        sec_obtenido = Decimal("0")
        sec_maximo = Decimal("0")

        for pregunta in seccion.preguntas.all():
            tipo = pregunta.tipo
            if tipo in Pregunta.TIPOS_NO_PUNTABLES:
                continue

            item = item_by_pregunta.get(pregunta.id)

            if tipo == Pregunta.Tipo.CUADRICULA:
                all_opts = list(pregunta.opciones.all())
                filas = list(pregunta.filas.all())
                if all_opts and filas:
                    sec_maximo += max(op.puntos for op in all_opts) * len(filas)
                if item:
                    for celda in item.celdas.all():
                        sec_obtenido += celda.opcion.puntos

            elif tipo == Pregunta.Tipo.ESCALA_LINEAL:
                cfg = pregunta.config or {}
                factor = Decimal(str(cfg.get("puntos_factor", 1)))
                max_val = Decimal(str(cfg.get("max", 5)))
                sec_maximo += max_val * factor
                if item and item.valor_texto:
                    try:
                        sec_obtenido += Decimal(item.valor_texto) * factor
                    except Exception:
                        pass

            elif tipo == Pregunta.Tipo.SI_NO:
                cfg = pregunta.config or {}
                pts_si = Decimal(str(cfg.get("puntos_si", 1)))
                pts_no = Decimal(str(cfg.get("puntos_no", 0)))
                sec_maximo += max(pts_si, pts_no)
                if item:
                    if item.valor_texto == "SI":
                        sec_obtenido += pts_si
                    elif item.valor_texto == "NO":
                        sec_obtenido += pts_no

            else:  # OPCION_UNICA, CASILLAS, LISTA_DESPLEGABLE
                all_opts = list(pregunta.opciones.all())
                positive_opts = [op for op in all_opts if op.puntos > 0]
                if tipo == Pregunta.Tipo.CASILLAS:
                    sec_maximo += sum(op.puntos for op in positive_opts)
                else:
                    sec_maximo += max((op.puntos for op in all_opts), default=Decimal("0"))
                if item:
                    for opcion in item.opciones_seleccionadas.all():
                        sec_obtenido += opcion.puntos

        sec_porcentaje = (
            round(sec_obtenido / sec_maximo * Decimal("100"), 2)
            if sec_maximo > 0
            else Decimal("0")
        )
        resultado_secciones.append({
            "seccion_id": seccion.id,
            "peso": seccion.peso,
            "obtenido": sec_obtenido,
            "maximo": sec_maximo,
            "porcentaje": sec_porcentaje,
        })
        puntaje_obtenido_total += sec_obtenido
        puntaje_maximo_total += sec_maximo

    porcentaje_ponderado = round(
        sum(s["porcentaje"] * s["peso"] / Decimal("100") for s in resultado_secciones),
        2,
    )

    return {
        "secciones": resultado_secciones,
        "porcentaje_ponderado": porcentaje_ponderado,
        "puntaje_obtenido_total": puntaje_obtenido_total,
        "puntaje_maximo_total": puntaje_maximo_total,
    }


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

    @action(detail=True, methods=["post"])
    def duplicar(self, request, pk=None):
        """Clona el formulario (estructura completa, sin respuestas) en otro periodo.

        Copia secciones, preguntas (con opciones/filas/config) y niveles de
        desempeño hacia un nuevo Formulario en estado BORRADOR y versión 1.
        No copia respuestas — el original permanece intacto para preservar
        el historial de profesores que ya respondieron.
        """
        original = self.get_object()
        periodo_id = request.data.get("periodo")
        titulo = (request.data.get("titulo") or "").strip()
        if not titulo:
            titulo = f"{original.titulo} (copia)"

        try:
            periodo = Periodo.objects.get(pk=periodo_id)
        except (Periodo.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"periodo": ["Periodo no válido."]})
        self._validar_periodo_habilitado(periodo)

        with transaction.atomic():
            nuevo = Formulario.objects.create(
                titulo=titulo,
                descripcion=original.descripcion,
                periodo=periodo,
                estado=Formulario.Estado.BORRADOR,
                version=1,
                una_respuesta_por_profesor=original.una_respuesta_por_profesor,
                created_by=request.user,
            )
            for nivel in original.niveles.all():
                NivelDesempeno.objects.create(
                    formulario=nuevo,
                    nombre=nivel.nombre,
                    porcentaje_min=nivel.porcentaje_min,
                    porcentaje_max=nivel.porcentaje_max,
                    observacion=nivel.observacion,
                    color=nivel.color,
                    orden=nivel.orden,
                )
            seccion_map = {}
            for seccion in original.secciones.order_by("orden"):
                nueva_seccion = Seccion.objects.create(
                    formulario=nuevo,
                    titulo=seccion.titulo,
                    descripcion=seccion.descripcion,
                    orden=seccion.orden,
                    peso=seccion.peso,
                )
                seccion_map[seccion.id] = nueva_seccion
            for pregunta in original.preguntas.order_by("orden"):
                nueva_pregunta = Pregunta.objects.create(
                    formulario=nuevo,
                    seccion=seccion_map.get(pregunta.seccion_id),
                    tipo=pregunta.tipo,
                    texto=pregunta.texto,
                    ayuda=pregunta.ayuda,
                    obligatoria=pregunta.obligatoria,
                    orden=pregunta.orden,
                    config=pregunta.config,
                )
                for opcion in pregunta.opciones.order_by("orden"):
                    OpcionPregunta.objects.create(
                        pregunta=nueva_pregunta,
                        texto=opcion.texto,
                        valor=opcion.valor,
                        puntos=opcion.puntos,
                        orden=opcion.orden,
                    )
                for fila in pregunta.filas.order_by("orden"):
                    FilaCuadricula.objects.create(
                        pregunta=nueva_pregunta,
                        texto=fila.texto,
                        orden=fila.orden,
                    )

        serializer = FormularioSerializer(nuevo, context={"request": request})
        return Response(serializer.data, status=201)

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

        # — Promedio por sección (agrega RespuestaSeccion de la versión actual) —
        por_seccion = []
        for seccion in formulario.secciones.order_by("orden"):
            rs_qs = RespuestaSeccion.objects.filter(
                respuesta__formulario=formulario,
                respuesta__estado=Respuesta.Estado.ENVIADO,
                respuesta__version_formulario=version,
                seccion=seccion,
            )
            promedio_sec = rs_qs.aggregate(avg=Avg("porcentaje"))["avg"]
            por_seccion.append({
                "seccion_id": seccion.id,
                "titulo": seccion.titulo,
                "peso": float(seccion.peso),
                "promedio_porcentaje": (
                    round(float(promedio_sec), 2) if promedio_sec is not None else None
                ),
                "total_con_datos": rs_qs.count(),
            })

        return Response({
            "formulario_id": formulario.id,
            "titulo": formulario.titulo,
            "version": int(version),
            "total_respuestas_enviadas": total_enviadas,
            "promedio_porcentaje": promedio_general,
            "distribucion_niveles": distribucion_niveles,
            "sin_nivel_asignado": sin_nivel,
            "por_seccion": por_seccion,
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
        try:
            serializer.save()
        except ProtectedError:
            raise ValidationError({
                "non_field_errors": [
                    "No se pueden eliminar opciones o filas referenciadas por respuestas existentes."
                ]
            })

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
                    "secciones_resultado__seccion",
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

        # — Calcular puntaje ponderado por sección —
        resultado = _calcular_puntaje(respuesta)
        porcentaje_ponderado = resultado["porcentaje_ponderado"]
        nivel = _asignar_nivel(respuesta.formulario, porcentaje_ponderado)

        # — Persistir en transacción atómica —
        with transaction.atomic():
            respuesta.estado = Respuesta.Estado.ENVIADO
            respuesta.enviado_at = timezone.now()
            respuesta.puntaje_obtenido = resultado["puntaje_obtenido_total"]
            respuesta.puntaje_maximo = resultado["puntaje_maximo_total"]
            respuesta.porcentaje = porcentaje_ponderado
            respuesta.nivel_desempeno = nivel
            respuesta.save(update_fields=[
                "estado", "enviado_at",
                "puntaje_obtenido", "puntaje_maximo", "porcentaje",
                "nivel_desempeno",
            ])

            respuesta.secciones_resultado.all().delete()
            for sec_data in resultado["secciones"]:
                RespuestaSeccion.objects.create(
                    respuesta=respuesta,
                    seccion_id=sec_data["seccion_id"],
                    peso=sec_data["peso"],
                    puntaje_obtenido=sec_data["obtenido"],
                    puntaje_maximo=sec_data["maximo"],
                    porcentaje=sec_data["porcentaje"],
                )

        serializer = self.get_serializer(respuesta)
        return Response(serializer.data)
