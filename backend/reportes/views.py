"""Vistas de reportes y dashboard — solo agregación ORM, sin modelos propios."""

from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profesor
from autoevaluacion.models import Formulario, Respuesta
from catalogos.models import Departamento, Licenciatura, Periodo
from core.permissions import IsAdmin
from documentos.models import CartaTematica, RequisitoRecuperacion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _periodo_o_activo(periodo_id):
    """Devuelve el Periodo indicado o el activo; None si no hay ninguno."""
    if periodo_id:
        return get_object_or_404(Periodo, id=periodo_id)
    return Periodo.objects.filter(activo=True).first()


def _serializar_periodo(periodo):
    if not periodo:
        return None
    return {"id": periodo.id, "clave": periodo.clave, "activo": periodo.activo}


def _conteos_documento(qs):
    """Conteos por estado. Tras retirar ENVIADO, solo hay BORRADOR/PUBLICADO."""
    total = qs.count()
    return {
        "total": total,
        "borrador": qs.filter(estado="BORRADOR").count(),
        "publicado": qs.filter(estado="PUBLICADO").count(),
    }


# ---------------------------------------------------------------------------
# Dashboard general
# ---------------------------------------------------------------------------


class DashboardView(APIView):
    """
    GET /api/v1/reportes/dashboard/
    ?periodo=<id>   — opcional; por defecto el periodo activo

    Métricas generales: profesores, documentos por tipo/estado,
    formularios y respuestas de autoevaluación.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        periodo = _periodo_o_activo(request.query_params.get("periodo"))

        # Profesores activos
        total_profesores = Profesor.objects.filter(estado=True).count()

        # Documentos del periodo (o todos si no hay periodo)
        cartas_qs = CartaTematica.objects.all()
        requisitos_qs = RequisitoRecuperacion.objects.all()
        formularios_qs = Formulario.objects.all()
        respuestas_qs = Respuesta.objects.filter(estado=Respuesta.Estado.ENVIADO)

        if periodo:
            cartas_qs = cartas_qs.filter(periodo=periodo)
            requisitos_qs = requisitos_qs.filter(periodo=periodo)
            formularios_qs = formularios_qs.filter(periodo=periodo)
            respuestas_qs = respuestas_qs.filter(formulario__periodo=periodo)

        formularios_total = formularios_qs.count()
        formularios_data = {
            "total": formularios_total,
            "borrador": formularios_qs.filter(estado=Formulario.Estado.BORRADOR).count(),
            "publicado": formularios_qs.filter(estado=Formulario.Estado.PUBLICADO).count(),
            "cerrado": formularios_qs.filter(estado=Formulario.Estado.CERRADO).count(),
        }

        return Response(
            {
                "periodo": _serializar_periodo(periodo),
                "profesores": {"total_activos": total_profesores},
                "cartas_tematicas": _conteos_documento(cartas_qs),
                "requisitos_recuperacion": _conteos_documento(requisitos_qs),
                "autoevaluacion": {
                    "formularios": formularios_data,
                    "respuestas_enviadas": respuestas_qs.count(),
                },
            }
        )


# ---------------------------------------------------------------------------
# Cumplimiento por departamento
# ---------------------------------------------------------------------------


class CumplimientoView(APIView):
    """
    GET /api/v1/reportes/cumplimiento/
    ?periodo=<id>       — opcional; por defecto activo
    ?departamento=<id>  — opcional; filtra un solo departamento

    Cumplimiento de documentos PUBLICADOS por departamento y licenciatura.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        periodo = _periodo_o_activo(request.query_params.get("periodo"))
        departamento_id = request.query_params.get("departamento")

        # Base de profesores activos
        profesores_base = Profesor.objects.filter(estado=True)

        # Filtro opcional por departamento
        deptos_qs = Departamento.objects.all()
        if departamento_id:
            deptos_qs = deptos_qs.filter(id=departamento_id)

        por_departamento = []
        for depto in deptos_qs.order_by("clave"):
            profs = profesores_base.filter(departamento=depto)
            total = profs.count()

            con_carta = con_requisito = 0
            if periodo and total:
                con_carta = (
                    CartaTematica.objects.filter(
                        profesor__in=profs,
                        periodo=periodo,
                        estado="PUBLICADO",
                    )
                    .values("profesor")
                    .distinct()
                    .count()
                )
                con_requisito = (
                    RequisitoRecuperacion.objects.filter(
                        profesor__in=profs,
                        periodo=periodo,
                        estado="PUBLICADO",
                    )
                    .values("profesor")
                    .distinct()
                    .count()
                )

            por_departamento.append(
                {
                    "departamento_id": depto.id,
                    "clave": depto.clave,
                    "nombre": depto.nombre,
                    "total_profesores": total,
                    "con_carta_publicada": con_carta,
                    "con_requisito_publicado": con_requisito,
                    "pct_carta": round(con_carta / total * 100, 1) if total else 0,
                    "pct_requisito": round(con_requisito / total * 100, 1) if total else 0,
                }
            )

        # Totales globales
        total_profs = sum(d["total_profesores"] for d in por_departamento)
        total_carta = sum(d["con_carta_publicada"] for d in por_departamento)
        total_req = sum(d["con_requisito_publicado"] for d in por_departamento)

        return Response(
            {
                "periodo": _serializar_periodo(periodo),
                "resumen": {
                    "total_profesores": total_profs,
                    "con_carta_publicada": total_carta,
                    "con_requisito_publicado": total_req,
                    "pct_carta": round(total_carta / total_profs * 100, 1) if total_profs else 0,
                    "pct_requisito": round(total_req / total_profs * 100, 1) if total_profs else 0,
                },
                "por_departamento": por_departamento,
            }
        )


# ---------------------------------------------------------------------------
# Cumplimiento por licenciatura
# ---------------------------------------------------------------------------


class CumplimientoLicenciaturaView(APIView):
    """
    GET /api/v1/reportes/cumplimiento-licenciatura/
    ?periodo=<id>        — opcional; por defecto activo
    ?licenciatura=<id>   — opcional; filtra una sola licenciatura

    Cumplimiento agrupado por UEA/licenciatura (documentos por UEA y periodo).
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        periodo = _periodo_o_activo(request.query_params.get("periodo"))
        licenciatura_id = request.query_params.get("licenciatura")

        lics_qs = Licenciatura.objects.select_related("departamento").all()
        if licenciatura_id:
            lics_qs = lics_qs.filter(id=licenciatura_id)

        por_licenciatura = []
        for lic in lics_qs.order_by("clave"):
            ueas = lic.ueas.filter(estado=True)

            cartas_qs = CartaTematica.objects.filter(uea__licenciatura=lic)
            requisitos_qs = RequisitoRecuperacion.objects.filter(uea__licenciatura=lic)
            if periodo:
                cartas_qs = cartas_qs.filter(periodo=periodo)
                requisitos_qs = requisitos_qs.filter(periodo=periodo)

            por_licenciatura.append(
                {
                    "licenciatura_id": lic.id,
                    "clave": lic.clave,
                    "nombre": lic.nombre,
                    "departamento": lic.departamento.nombre if lic.departamento else None,
                    "total_ueas_activas": ueas.count(),
                    "cartas_tematicas": _conteos_documento(cartas_qs),
                    "requisitos_recuperacion": _conteos_documento(requisitos_qs),
                }
            )

        return Response(
            {
                "periodo": _serializar_periodo(periodo),
                "por_licenciatura": por_licenciatura,
            }
        )


# ---------------------------------------------------------------------------
# Autoevaluación por profesor
# ---------------------------------------------------------------------------


class AutoevaluacionProfesoresView(APIView):
    """
    GET /api/v1/reportes/autoevaluacion-profesores/
    ?periodo=<id>       — opcional; por defecto activo
    ?departamento=<id>  — opcional; filtra por departamento del profesor

    Lista de profesores activos con el porcentaje obtenido en la
    autoevaluación del periodo (0 si no la han enviado), su número
    económico y su departamento.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        periodo = _periodo_o_activo(request.query_params.get("periodo"))
        departamento_id = request.query_params.get("departamento")

        profesores_qs = Profesor.objects.filter(estado=True).select_related("departamento")
        if departamento_id:
            profesores_qs = profesores_qs.filter(departamento_id=departamento_id)

        formulario = None
        porcentajes = {}
        if periodo:
            formulario = Formulario.objects.filter(periodo=periodo).order_by("-created_at").first()
            if formulario:
                respuestas = Respuesta.objects.filter(
                    formulario=formulario,
                    estado=Respuesta.Estado.ENVIADO,
                    version_formulario=formulario.version,
                )
                porcentajes = {r.profesor_id: r.porcentaje for r in respuestas}

        profesores = [
            {
                "id": profesor.id,
                "nombre_completo": profesor.nombre_completo,
                "numero_economico": profesor.numero_economico,
                "departamento_id": profesor.departamento_id,
                "departamento_nombre": profesor.departamento.nombre if profesor.departamento else None,
                "porcentaje": float(porcentajes.get(profesor.id, 0) or 0),
            }
            for profesor in profesores_qs.order_by("nombre_completo")
        ]

        return Response(
            {
                "periodo": _serializar_periodo(periodo),
                "formulario": (
                    {
                        "id": formulario.id,
                        "titulo": formulario.titulo,
                        "version": formulario.version,
                        "estado": formulario.estado,
                    }
                    if formulario else None
                ),
                "profesores": profesores,
            }
        )


# ---------------------------------------------------------------------------
# Resumen de autoevaluación
# ---------------------------------------------------------------------------


class ResumenAutoevaluacionView(APIView):
    """
    GET /api/v1/reportes/autoevaluacion/
    ?periodo=<id>  — opcional; por defecto activo

    Lista de formularios del periodo con tasa de respuesta.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        periodo = _periodo_o_activo(request.query_params.get("periodo"))

        formularios_qs = Formulario.objects.select_related("periodo")
        if periodo:
            formularios_qs = formularios_qs.filter(periodo=periodo)

        total_profesores = Profesor.objects.filter(estado=True).count()

        resultado = []
        for formulario in formularios_qs.order_by("-created_at"):
            respuestas_enviadas = formulario.respuestas.filter(
                estado=Respuesta.Estado.ENVIADO
            ).count()
            resultado.append(
                {
                    "formulario_id": formulario.id,
                    "titulo": formulario.titulo,
                    "estado": formulario.estado,
                    "published_at": formulario.published_at,
                    "closed_at": formulario.closed_at,
                    "respuestas_enviadas": respuestas_enviadas,
                    "total_profesores": total_profesores,
                    "tasa_respuesta": (
                        round(respuestas_enviadas / total_profesores * 100, 1)
                        if total_profesores
                        else 0
                    ),
                }
            )

        return Response(
            {
                "periodo": _serializar_periodo(periodo),
                "formularios": resultado,
            }
        )
