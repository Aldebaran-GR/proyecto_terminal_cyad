"""URLs del módulo Reportes."""

from django.urls import path

from .views import (
    CumplimientoLicenciaturaView,
    CumplimientoView,
    DashboardView,
    ResumenAutoevaluacionView,
)

urlpatterns = [
    path("reportes/dashboard/", DashboardView.as_view(), name="reporte-dashboard"),
    path("reportes/cumplimiento/", CumplimientoView.as_view(), name="reporte-cumplimiento"),
    path(
        "reportes/cumplimiento-licenciatura/",
        CumplimientoLicenciaturaView.as_view(),
        name="reporte-cumplimiento-licenciatura",
    ),
    path(
        "reportes/autoevaluacion/",
        ResumenAutoevaluacionView.as_view(),
        name="reporte-autoevaluacion",
    ),
]
