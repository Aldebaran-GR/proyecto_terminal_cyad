"""Tests del módulo Reportes (M5) — endpoints de agregación."""

import pytest
from rest_framework.test import APIClient

from accounts.models import Profesor, Usuario
from autoevaluacion.models import Formulario, Respuesta
from catalogos.models import Departamento, Licenciatura, Periodo, UEA
from documentos.models import CartaTematica, RequisitoRecuperacion


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin(db):
    return Usuario.objects.create_user(
        email="admin_rpt@cyad.uam.mx",
        nombre="Admin RPT",
        password="Admin1234!",
        rol=Usuario.Rol.ADMIN,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def depto(db):
    return Departamento.objects.create(clave="EDTRPT", nombre="EDT Reportes")


@pytest.fixture
def depto2(db):
    return Departamento.objects.create(clave="ICDRPT", nombre="ICD Reportes")


@pytest.fixture
def licenciatura(db, depto):
    return Licenciatura.objects.create(clave="DIRPT", nombre="DI Reportes", departamento=depto)


@pytest.fixture
def periodo(db):
    return Periodo.objects.create(
        clave="26-IRPT",
        fecha_inicio="2026-01-12",
        fecha_fin="2026-04-17",
        activo=True,
    )


@pytest.fixture
def uea(db, licenciatura):
    return UEA.objects.create(
        clave="RPT001",
        nombre="UEA Reportes",
        licenciatura=licenciatura,
    )


def _make_prof(db_fixture, email, nombre, depto):
    """Crea Usuario + Profesor en el depto indicado."""
    u = Usuario.objects.create_user(
        email=email, nombre=nombre, password="Prof1234!", rol=Usuario.Rol.PROFESOR
    )
    return Profesor.objects.create(
        usuario=u,
        nombre_completo=nombre,
        correo_institucional=email.replace("@cyad.", "@uam."),
        departamento=depto,
    )


def auth_admin(client):
    r = client.post(
        "/api/v1/auth/login/",
        {"email": "admin_rpt@cyad.uam.mx", "password": "Admin1234!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


def auth_as(client, email):
    r = client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": "Prof1234!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_admin_accede_dashboard(self, client, admin, periodo):
        auth_admin(client)
        r = client.get("/api/v1/reportes/dashboard/")
        assert r.status_code == 200
        assert "periodo" in r.data
        assert "profesores" in r.data
        assert "cartas_tematicas" in r.data
        assert "requisitos_recuperacion" in r.data
        assert "autoevaluacion" in r.data

    def test_dashboard_usa_periodo_activo(self, client, admin, periodo):
        auth_admin(client)
        r = client.get("/api/v1/reportes/dashboard/")
        assert r.status_code == 200
        assert r.data["periodo"]["clave"] == "26-IRPT"

    def test_dashboard_con_periodo_parametro(self, client, admin, periodo):
        auth_admin(client)
        r = client.get(f"/api/v1/reportes/dashboard/?periodo={periodo.id}")
        assert r.status_code == 200
        assert r.data["periodo"]["id"] == periodo.id

    def test_dashboard_cuenta_documentos(self, client, admin, depto, periodo, uea):
        profesor = _make_prof(None, "pdash@cyad.uam.mx", "P Dashboard", depto)
        CartaTematica.objects.create(
            profesor=profesor,
            uea=uea,
            periodo=periodo,
            nombre_grupo="G01",
            id_grupo="G01",
            horario="Lunes",
            modalidad="PRESENCIAL",
            estado="ENVIADO",
        )
        auth_admin(client)
        r = client.get(f"/api/v1/reportes/dashboard/?periodo={periodo.id}")
        assert r.status_code == 200
        assert r.data["cartas_tematicas"]["enviado"] >= 1
        assert r.data["cartas_tematicas"]["total"] >= 1

    def test_profesor_no_accede_dashboard(self, client, admin, depto, periodo):
        prof = _make_prof(None, "pnodash@cyad.uam.mx", "P NoDash", depto)
        auth_as(client, "pnodash@cyad.uam.mx")
        r = client.get("/api/v1/reportes/dashboard/")
        assert r.status_code == 403

    def test_dashboard_estructura_autoevaluacion(self, client, admin, periodo):
        formulario = Formulario.objects.create(
            titulo="F Dashboard",
            periodo=periodo,
            created_by=admin,
        )
        formulario.publicar()
        auth_admin(client)
        r = client.get(f"/api/v1/reportes/dashboard/?periodo={periodo.id}")
        assert r.status_code == 200
        assert r.data["autoevaluacion"]["formularios"]["publicado"] >= 1


# ---------------------------------------------------------------------------
# Cumplimiento por departamento
# ---------------------------------------------------------------------------


class TestCumplimiento:
    def test_cumplimiento_estructura(self, client, admin, depto, periodo):
        auth_admin(client)
        r = client.get("/api/v1/reportes/cumplimiento/")
        assert r.status_code == 200
        assert "resumen" in r.data
        assert "por_departamento" in r.data
        assert isinstance(r.data["por_departamento"], list)

    def test_cumplimiento_con_periodo(self, client, admin, depto, periodo):
        auth_admin(client)
        r = client.get(f"/api/v1/reportes/cumplimiento/?periodo={periodo.id}")
        assert r.status_code == 200
        assert r.data["periodo"]["id"] == periodo.id

    def test_cumplimiento_cuenta_enviados(self, client, admin, depto, periodo, uea):
        prof = _make_prof(None, "pcumpl@cyad.uam.mx", "P Cumpl", depto)
        CartaTematica.objects.create(
            profesor=prof, uea=uea, periodo=periodo,
            nombre_grupo="G01", id_grupo="G01",
            horario="L 10-12", modalidad="PRESENCIAL", estado="ENVIADO",
        )
        auth_admin(client)
        r = client.get(f"/api/v1/reportes/cumplimiento/?periodo={periodo.id}&departamento={depto.id}")
        assert r.status_code == 200
        depto_data = r.data["por_departamento"][0]
        assert depto_data["con_carta_enviada"] == 1
        assert depto_data["total_profesores"] >= 1

    def test_cumplimiento_no_cuenta_borradores(self, client, admin, depto, periodo, uea):
        prof = _make_prof(None, "pborrdr@cyad.uam.mx", "P Borrador", depto)
        CartaTematica.objects.create(
            profesor=prof, uea=uea, periodo=periodo,
            nombre_grupo="G01", id_grupo="G01",
            horario="L 10-12", modalidad="PRESENCIAL", estado="BORRADOR",
        )
        auth_admin(client)
        r = client.get(f"/api/v1/reportes/cumplimiento/?periodo={periodo.id}&departamento={depto.id}")
        assert r.status_code == 200
        depto_data = r.data["por_departamento"][0]
        assert depto_data["con_carta_enviada"] == 0

    def test_cumplimiento_filtro_departamento(self, client, admin, depto, depto2, periodo):
        auth_admin(client)
        r = client.get(f"/api/v1/reportes/cumplimiento/?departamento={depto.id}")
        assert r.status_code == 200
        assert len(r.data["por_departamento"]) == 1
        assert r.data["por_departamento"][0]["departamento_id"] == depto.id

    def test_cumplimiento_pct_calculo(self, client, admin, depto, periodo, uea):
        # 2 profesores, 1 envió carta
        p1 = _make_prof(None, "ppct1@cyad.uam.mx", "P Pct1", depto)
        _make_prof(None, "ppct2@cyad.uam.mx", "P Pct2", depto)
        CartaTematica.objects.create(
            profesor=p1, uea=uea, periodo=periodo,
            nombre_grupo="G01", id_grupo="G01",
            horario="L 10-12", modalidad="PRESENCIAL", estado="ENVIADO",
        )
        auth_admin(client)
        r = client.get(f"/api/v1/reportes/cumplimiento/?periodo={periodo.id}&departamento={depto.id}")
        assert r.status_code == 200
        depto_data = r.data["por_departamento"][0]
        assert depto_data["total_profesores"] == 2
        assert depto_data["con_carta_enviada"] == 1
        assert depto_data["pct_carta"] == 50.0

    def test_profesor_no_accede_cumplimiento(self, client, admin, depto):
        prof = _make_prof(None, "pnocumpl@cyad.uam.mx", "P NoCumpl", depto)
        auth_as(client, "pnocumpl@cyad.uam.mx")
        r = client.get("/api/v1/reportes/cumplimiento/")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Cumplimiento por licenciatura
# ---------------------------------------------------------------------------


class TestCumplimientoLicenciatura:
    def test_cumplimiento_licenciatura_estructura(self, client, admin, licenciatura, periodo):
        auth_admin(client)
        r = client.get("/api/v1/reportes/cumplimiento-licenciatura/")
        assert r.status_code == 200
        assert "por_licenciatura" in r.data
        assert isinstance(r.data["por_licenciatura"], list)

    def test_cumplimiento_licenciatura_filtro(self, client, admin, licenciatura, periodo):
        auth_admin(client)
        r = client.get(f"/api/v1/reportes/cumplimiento-licenciatura/?licenciatura={licenciatura.id}")
        assert r.status_code == 200
        assert len(r.data["por_licenciatura"]) == 1
        assert r.data["por_licenciatura"][0]["licenciatura_id"] == licenciatura.id

    def test_cumplimiento_licenciatura_cuenta_cartas(self, client, admin, depto, licenciatura, periodo, uea):
        prof = _make_prof(None, "plic@cyad.uam.mx", "P Lic", depto)
        CartaTematica.objects.create(
            profesor=prof, uea=uea, periodo=periodo,
            nombre_grupo="G01", id_grupo="G01",
            horario="L 10-12", modalidad="PRESENCIAL", estado="ENVIADO",
        )
        auth_admin(client)
        r = client.get(
            f"/api/v1/reportes/cumplimiento-licenciatura/"
            f"?periodo={periodo.id}&licenciatura={licenciatura.id}"
        )
        assert r.status_code == 200
        lic_data = r.data["por_licenciatura"][0]
        assert lic_data["cartas_tematicas"]["enviado"] == 1


# ---------------------------------------------------------------------------
# Resumen autoevaluación
# ---------------------------------------------------------------------------


class TestResumenAutoevaluacion:
    def test_resumen_autoevaluacion(self, client, admin, periodo):
        Formulario.objects.create(titulo="F1", periodo=periodo, created_by=admin)
        auth_admin(client)
        r = client.get("/api/v1/reportes/autoevaluacion/")
        assert r.status_code == 200
        assert "formularios" in r.data
        assert len(r.data["formularios"]) >= 1

    def test_tasa_respuesta_calculada(self, client, admin, depto, periodo):
        prof = _make_prof(None, "ptasa@cyad.uam.mx", "P Tasa", depto)
        formulario = Formulario.objects.create(
            titulo="F Tasa", periodo=periodo, created_by=admin
        )
        formulario.publicar()
        Respuesta.objects.create(
            formulario=formulario,
            profesor=prof,
            estado=Respuesta.Estado.ENVIADO,
        )
        auth_admin(client)
        r = client.get(f"/api/v1/reportes/autoevaluacion/?periodo={periodo.id}")
        assert r.status_code == 200
        f_data = r.data["formularios"][0]
        assert f_data["respuestas_enviadas"] == 1
        assert f_data["tasa_respuesta"] > 0

    def test_profesor_no_accede_resumen(self, client, admin, depto):
        prof = _make_prof(None, "pnoae@cyad.uam.mx", "P NoAE", depto)
        auth_as(client, "pnoae@cyad.uam.mx")
        r = client.get("/api/v1/reportes/autoevaluacion/")
        assert r.status_code == 403
