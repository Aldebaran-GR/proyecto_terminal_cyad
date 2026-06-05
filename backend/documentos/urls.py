from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CartaTematicaViewSet, RequisitoRecuperacionViewSet

router = DefaultRouter()
router.register("cartas-tematicas", CartaTematicaViewSet, basename="carta-tematica")
router.register("requisitos-recuperacion", RequisitoRecuperacionViewSet, basename="requisito-recuperacion")

urlpatterns = [path("", include(router.urls))]
