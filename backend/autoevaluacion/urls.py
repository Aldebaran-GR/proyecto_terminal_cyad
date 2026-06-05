"""URLs del módulo Autoevaluación."""

from rest_framework.routers import DefaultRouter

from .views import (
    FormularioViewSet,
    FormulariosDisponiblesViewSet,
    NivelDesempenoViewSet,
    PreguntaViewSet,
    RespuestaViewSet,
    SeccionViewSet,
)

router = DefaultRouter()
router.register(r"formularios", FormularioViewSet, basename="formulario")
router.register(r"secciones", SeccionViewSet, basename="seccion")
router.register(r"preguntas", PreguntaViewSet, basename="pregunta")
router.register(r"niveles-desempeno", NivelDesempenoViewSet, basename="nivel-desempeno")
router.register(r"formularios-disponibles", FormulariosDisponiblesViewSet, basename="formulario-disponible")
router.register(r"respuestas", RespuestaViewSet, basename="respuesta")

urlpatterns = router.urls
