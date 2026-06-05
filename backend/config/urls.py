"""Ruteo raíz del proyecto.

Las rutas de la API viven bajo /api/v1/ y se agregan por app conforme avanzan
los hitos del desarrollo.
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(_request):
    return JsonResponse({"status": "ok", "service": "proyecto-terminal-cyad"})


api_v1_patterns = [
    path("health/", health, name="health"),
    path("", include("accounts.urls")),
    path("", include("catalogos.urls")),
    path("", include("documentos.urls")),
    path("", include("autoevaluacion.urls")),
    path("", include("reportes.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1_patterns, "api"))),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
