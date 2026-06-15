from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AreaViewSet,
    DepartamentoViewSet,
    LicenciaturaViewSet,
    PeriodoViewSet,
    PosgradoViewSet,
    PublicLicenciaturaListView,
    PublicUEAListView,
    UEAViewSet,
)

router = DefaultRouter()
router.register("departamentos", DepartamentoViewSet, basename="departamento")
router.register("licenciaturas", LicenciaturaViewSet, basename="licenciatura")
router.register("posgrados", PosgradoViewSet, basename="posgrado")
router.register("areas", AreaViewSet, basename="area")
router.register("uea", UEAViewSet, basename="uea")
router.register("periodos", PeriodoViewSet, basename="periodo")

urlpatterns = [
    path("", include(router.urls)),
    # Vistas públicas (sin auth) — usadas por la home pública para los
    # selectores en cascada (Licenciatura → UEA).
    path("publico/licenciaturas/", PublicLicenciaturaListView.as_view(), name="public-licenciaturas"),
    path("publico/uea/", PublicUEAListView.as_view(), name="public-uea"),
]
