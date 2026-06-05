from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DepartamentoViewSet, LicenciaturaViewSet, PeriodoViewSet, UEAViewSet

router = DefaultRouter()
router.register("departamentos", DepartamentoViewSet, basename="departamento")
router.register("licenciaturas", LicenciaturaViewSet, basename="licenciatura")
router.register("uea", UEAViewSet, basename="uea")
router.register("periodos", PeriodoViewSet, basename="periodo")

urlpatterns = [path("", include(router.urls))]
