from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CartaTematicaViewSet,
    PublicCartaListView,
    PublicCartaView,
    PublicRequisitoListView,
    PublicRequisitoView,
    RequisitoRecuperacionViewSet,
)

router = DefaultRouter()
router.register("cartas-tematicas", CartaTematicaViewSet, basename="carta-tematica")
router.register("requisitos-recuperacion", RequisitoRecuperacionViewSet, basename="requisito-recuperacion")

urlpatterns = [
    path("", include(router.urls)),
    # Vistas públicas (sin auth)
    path(
        "publico/cartas/",
        PublicCartaListView.as_view(),
        name="public-cartas-list",
    ),
    path(
        "publico/cartas/<int:pk>/",
        PublicCartaView.as_view(),
        name="public-carta",
    ),
    path(
        "publico/requisitos/",
        PublicRequisitoListView.as_view(),
        name="public-requisitos-list",
    ),
    path(
        "publico/requisitos/<int:pk>/",
        PublicRequisitoView.as_view(),
        name="public-requisito",
    ),
]
