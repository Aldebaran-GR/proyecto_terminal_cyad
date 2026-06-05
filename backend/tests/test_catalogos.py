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
    def test_solo_un_activo(self, client, admin, db):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        import datetime
        p1 = client.post("/api/v1/periodos/", {
            "clave": "26-I", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-04-30", "activo": True
        }, format="json")
        p2 = client.post("/api/v1/periodos/", {
            "clave": "26-P", "fecha_inicio": "2026-05-01", "fecha_fin": "2026-08-31", "activo": True
        }, format="json")
        assert p1.status_code == 201
        assert p2.status_code == 201
        from catalogos.models import Periodo
        assert Periodo.objects.filter(activo=True).count() == 1

    def test_fecha_fin_anterior_inicio(self, client, admin, db):
        auth(client, "admin2@cyad.uam.mx", "Admin1234!")
        r = client.post("/api/v1/periodos/", {
            "clave": "XX-I", "fecha_inicio": "2026-04-30", "fecha_fin": "2026-01-01", "activo": False
        }, format="json")
        assert r.status_code == 400


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
