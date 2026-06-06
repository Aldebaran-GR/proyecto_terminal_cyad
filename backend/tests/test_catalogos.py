"""Tests de catálogos institucionales — M2."""

import io
import pytest
from rest_framework.test import APIClient

from accounts.models import Usuario
from catalogos.models import Departamento, Licenciatura, Periodo, UEA


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin(db):
    return Usuario.objects.create_user(
        email="admin2@cyad.uam.mx", nombre="Admin2", password="Admin1234!",
        rol=Usuario.Rol.ADMIN, is_staff=True, is_superuser=True,
    )


@pytest.fixture
def profesor(db):
    return Usuario.objects.create_user(
        email="prof2@cyad.uam.mx", nombre="Prof2", password="Profesor1234!",
        rol=Usuario.Rol.PROFESOR,
    )


def auth(client, email, password):
    r = client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


@pytest.fixture
def depto(db):
    return Departamento.objects.create(clave="EDT", nombre="Evaluación del Diseño en el Tiempo")


@pytest.fixture
def licenciatura(db, depto):
    return Licenciatura.objects.create(clave="DI", nombre="Diseño Industrial", departamento=depto)


class TestDepartamentos:
    def test_lista_autenticado(self, client, depto, profesor):
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        r = client.get("/api/v1/departamentos/")
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_crear_solo_admin(self, client, admin):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post("/api/v1/departamentos/", {"clave": "NUEVO", "nombre": "Nuevo Depto"}, format="json")
        assert r.status_code == 201

    def test_crear_bloqueado_profesor(self, client, profesor):
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        r = client.post("/api/v1/departamentos/", {"clave": "NUEVO", "nombre": "Nuevo"}, format="json")
        assert r.status_code == 403

    def test_clave_unica(self, client, admin, depto):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post("/api/v1/departamentos/", {"clave": "EDT", "nombre": "Duplicado"}, format="json")
        assert r.status_code == 400


class TestLicenciaturas:
    def test_lista(self, client, licenciatura, profesor):
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        r = client.get("/api/v1/licenciaturas/")
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_crear_admin(self, client, admin, depto):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post(
            "/api/v1/licenciaturas/",
            {"clave": "ARQ", "nombre": "Arquitectura", "departamento": depto.id},
            format="json",
        )
        assert r.status_code == 201
        assert r.data["departamento_nombre"] == depto.nombre


class TestPeriodos:
    def test_solo_un_activo_por_recurso(self, client, admin, db):
        """Al activar el mismo recurso en dos periodos, el segundo apaga al primero."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        p1 = client.post("/api/v1/periodos/", {
            "clave": "26-I", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-04-30",
            "activo_cartas": True, "activo_requisitos": True, "activo_autoevaluacion": True,
        }, format="json")
        p2 = client.post("/api/v1/periodos/", {
            "clave": "26-P", "fecha_inicio": "2026-05-01", "fecha_fin": "2026-08-31",
            "activo_cartas": True, "activo_requisitos": True, "activo_autoevaluacion": True,
        }, format="json")
        assert p1.status_code == 201
        assert p2.status_code == 201
        from catalogos.models import Periodo
        # Exactamente un periodo activo por cada recurso, no globalmente.
        assert Periodo.objects.filter(activo_cartas=True).count() == 1
        assert Periodo.objects.filter(activo_requisitos=True).count() == 1
        assert Periodo.objects.filter(activo_autoevaluacion=True).count() == 1
        # `activo` legado sigue siendo OR de los tres → solo 1 periodo lo tiene.
        assert Periodo.objects.filter(activo=True).count() == 1

    def test_activos_separados_por_recurso(self, client, admin, db):
        """26-P puede ser activo para Requisitos/AE y 26-O para Cartas al mismo tiempo."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        p_actual = client.post("/api/v1/periodos/", {
            "clave": "26-P", "fecha_inicio": "2026-05-01", "fecha_fin": "2026-08-31",
            "activo_requisitos": True, "activo_autoevaluacion": True,
        }, format="json")
        p_siguiente = client.post("/api/v1/periodos/", {
            "clave": "26-O", "fecha_inicio": "2026-09-01", "fecha_fin": "2026-12-31",
            "activo_cartas": True,
        }, format="json")
        assert p_actual.status_code == 201
        assert p_siguiente.status_code == 201
        r = client.get("/api/v1/periodos/activos/")
        assert r.status_code == 200
        assert r.data["cartas"]["clave"] == "26-O"
        assert r.data["requisitos"]["clave"] == "26-P"
        assert r.data["autoevaluacion"]["clave"] == "26-P"

    def test_fecha_fin_anterior_inicio(self, client, admin, db):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post("/api/v1/periodos/", {
            "clave": "XX-I", "fecha_inicio": "2026-04-30", "fecha_fin": "2026-01-01", "activo": False
        }, format="json")
        assert r.status_code == 400

    def test_eliminar_periodo_activo_bloqueado(self, client, admin, db):
        """Un periodo activo para algún recurso no puede ser eliminado."""
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        from catalogos.models import Periodo
        p = Periodo.objects.create(
            clave="DEL-A", fecha_inicio="2026-01-01", fecha_fin="2026-04-30",
            activo_cartas=True,
        )
        preview = client.get(f"/api/v1/periodos/{p.id}/preview-eliminacion/")
        assert preview.status_code == 200
        assert preview.data["puede_eliminar"] is False
        r = client.delete(f"/api/v1/periodos/{p.id}/")
        assert r.status_code == 400
        assert Periodo.objects.filter(pk=p.id).exists()

    def test_eliminar_periodo_inactivo_en_cascada(self, client, admin, db):
        """Un periodo inactivo se elimina junto con sus cartas/requisitos/formularios/respuestas."""
        from accounts.models import Profesor, Usuario
        from autoevaluacion.models import Formulario, Respuesta
        from catalogos.models import (
            Departamento, Licenciatura, Periodo, UEA,
        )
        from documentos.models import CartaTematica, RequisitoRecuperacion

        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        # Catálogos mínimos
        depto = Departamento.objects.create(clave="DLT", nombre="Del Test")
        lic = Licenciatura.objects.create(clave="DLTL", nombre="DelLic", departamento=depto)
        uea = UEA.objects.create(clave="DELUEA", nombre="UEA Del", licenciatura=lic)
        # Periodo INACTIVO (ningún flag prendido)
        p_old = Periodo.objects.create(
            clave="DEL-OLD", fecha_inicio="2025-01-01", fecha_fin="2025-04-30",
        )
        # Periodo independiente para verificar que no se borra
        p_otro = Periodo.objects.create(
            clave="DEL-OTRO", fecha_inicio="2024-01-01", fecha_fin="2024-04-30",
        )
        u_admin = Usuario.objects.get(email="admin2@cyad.uam.mx")
        # Profesor + perfil
        u_prof = Usuario.objects.create_user(
            email="pdel@uam.mx", nombre="P Del", password="Profesor1234!",
            rol=Usuario.Rol.PROFESOR,
        )
        prof = Profesor.objects.create(
            usuario=u_prof, nombre_completo="P Del",
            correo_institucional="pdel@uam.mx", departamento=depto,
        )
        # Documentos en p_old
        CartaTematica.objects.create(
            profesor=prof, uea=uea, periodo=p_old,
            nombre_grupo="G", id_grupo="DEL-G1", horario="Lun 9-11",
        )
        RequisitoRecuperacion.objects.create(
            profesor=prof, uea=uea, periodo=p_old,
            nombre_grupo="G", id_grupo="DEL-R1", horario="Lun 9-11",
        )
        # Formulario en p_old + respuesta del profesor
        form = Formulario.objects.create(
            titulo="F Del", periodo=p_old, created_by=u_admin,
        )
        Respuesta.objects.create(formulario=form, profesor=prof, version_formulario=1)
        # Documento en p_otro (no debe verse afectado)
        CartaTematica.objects.create(
            profesor=prof, uea=uea, periodo=p_otro,
            nombre_grupo="G", id_grupo="DEL-OTRO-G1", horario="Lun 9-11",
        )

        # Preview
        preview = client.get(f"/api/v1/periodos/{p_old.id}/preview-eliminacion/")
        assert preview.status_code == 200
        assert preview.data["puede_eliminar"] is True
        dep = preview.data["dependencias"]
        assert dep["cartas_tematicas"] == 1
        assert dep["requisitos_recuperacion"] == 1
        assert dep["formularios_autoevaluacion"] == 1
        assert dep["respuestas_autoevaluacion"] == 1

        # Eliminar
        r = client.delete(f"/api/v1/periodos/{p_old.id}/")
        assert r.status_code in (200, 204), r.data
        # El periodo se fue + sus documentos / formularios / respuestas
        assert not Periodo.objects.filter(pk=p_old.id).exists()
        assert CartaTematica.objects.filter(periodo_id=p_old.id).count() == 0
        assert RequisitoRecuperacion.objects.filter(periodo_id=p_old.id).count() == 0
        assert Formulario.objects.filter(periodo_id=p_old.id).count() == 0
        # El otro periodo y su carta siguen intactos
        assert Periodo.objects.filter(pk=p_otro.id).exists()
        assert CartaTematica.objects.filter(periodo_id=p_otro.id).count() == 1


class TestUEA:
    def test_lista_con_filtro(self, client, profesor, licenciatura):
        auth(client, "prof2@cyad.uam.mx", "Profesor1234!")
        UEA.objects.create(clave="1400001", nombre="Taller I", licenciatura=licenciatura, tipo="OBL")
        r = client.get(f"/api/v1/uea/?licenciatura={licenciatura.id}")
        assert r.status_code == 200
        assert r.data["count"] == 1

    def test_import_csv(self, client, admin, licenciatura):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        csv_content = (
            "clave,nombre,licenciatura_clave,trimestre,etapa,tipo,creditos\n"
            "9900001,UEA CSV Test,DI,3,TB,OBL,8\n"
            "9900002,UEA CSV Test 2,DI,4,TB,OBL,6\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "test.csv"
        r = client.post("/api/v1/uea/import-csv/", {"file": csv_file}, format="multipart")
        assert r.status_code == 200
        assert r.data["created"] == 2
        assert UEA.objects.filter(clave__startswith="9900").count() == 2

    def test_import_csv_licenciatura_invalida(self, client, admin, db):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        csv_content = (
            "clave,nombre,licenciatura_clave,trimestre,etapa,tipo,creditos\n"
            "9910001,UEA Mala,INVALIDA,1,TG,OBL,4\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "bad.csv"
        r = client.post("/api/v1/uea/import-csv/", {"file": csv_file}, format="multipart")
        assert r.status_code == 200
        assert len(r.data["errors"]) == 1
        assert r.data["created"] == 0
