"""Tests de documentos académicos (Carta Temática + Requisitos) — M3."""

import pytest
from rest_framework.test import APIClient

from accounts.models import Profesor, Usuario
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
        email="admin_doc@cyad.uam.mx", nombre="Admin Doc", password="Admin1234!",
        rol=Usuario.Rol.ADMIN, is_staff=True, is_superuser=True,
    )


@pytest.fixture
def usuario_prof1(db):
    return Usuario.objects.create_user(
        email="prof_doc1@cyad.uam.mx", nombre="Profesor Doc 1", password="Prof1234!",
        rol=Usuario.Rol.PROFESOR,
    )


@pytest.fixture
def usuario_prof2(db):
    return Usuario.objects.create_user(
        email="prof_doc2@cyad.uam.mx", nombre="Profesor Doc 2", password="Prof1234!",
        rol=Usuario.Rol.PROFESOR,
    )


@pytest.fixture
def depto(db):
    return Departamento.objects.create(clave="EDTD", nombre="Evaluación del Diseño")


@pytest.fixture
def licenciatura(db, depto):
    return Licenciatura.objects.create(clave="DID", nombre="Diseño Industrial Doc", departamento=depto)


@pytest.fixture
def uea(db, licenciatura):
    return UEA.objects.create(clave="1403001D", nombre="Diseño de Objetos I", licenciatura=licenciatura)


@pytest.fixture
def periodo(db):
    return Periodo.objects.create(
        clave="26-ID", fecha_inicio="2026-01-12", fecha_fin="2026-04-17",
        # Activo para los 3 recursos: las pruebas crean tanto Cartas como
        # Requisitos y la auto-asignación de periodo necesita el flag correcto.
        activo_cartas=True, activo_requisitos=True, activo_autoevaluacion=True,
    )


@pytest.fixture
def profesor1(db, usuario_prof1, depto):
    return Profesor.objects.create(
        usuario=usuario_prof1,
        nombre_completo="Profesor Doc 1",
        correo_institucional="prof_doc1@uam.mx",
        departamento=depto,
    )


@pytest.fixture
def profesor2(db, usuario_prof2, depto):
    return Profesor.objects.create(
        usuario=usuario_prof2,
        nombre_completo="Profesor Doc 2",
        correo_institucional="prof_doc2@uam.mx",
        departamento=depto,
    )


def auth(client, email, password):
    r = client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


def carta_payload(uea_id, periodo_id, profesor_id=None, id_grupo="G01"):
    p = {
        "uea": uea_id,
        "periodo": periodo_id,
        "nombre_grupo": "Grupo Test",
        "id_grupo": id_grupo,
        "horario": "Lunes 10-12",
        "modalidad": "PRESENCIAL",
        "objetivo_general": "Objetivo de prueba",
        "temas": [
            {
                "orden": 1,
                "nombre": "Tema 1",
                "objetivo": "Aprender X",
                "num_sesiones": 3,
                "subtemas": [{"orden": 1, "descripcion": "Subtema A"}],
            }
        ],
        "bibliografias": [{"tipo": "BASICA", "referencia": "Autor, A. (2024). Libro."}],
        "criterios": [{"descripcion": "Examen parcial", "ponderacion": 40}],
    }
    if profesor_id:
        p["profesor"] = profesor_id
    return p


# ---------------------------------------------------------------------------
# Carta Temática — CRUD
# ---------------------------------------------------------------------------

class TestCartaTematicaCRUD:
    def test_crear_carta(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        r = client.post(
            "/api/v1/cartas-tematicas/",
            carta_payload(uea.id, periodo.id),
            format="json",
        )
        assert r.status_code == 201
        assert r.data["estado"] == "BORRADOR"
        assert r.data["profesor_nombre"] == "Profesor Doc 1"
        assert len(r.data["temas"]) == 1
        assert len(r.data["temas"][0]["subtemas"]) == 1
        assert len(r.data["bibliografias"]) == 1
        assert len(r.data["criterios"]) == 1

    def test_listar_solo_propias(self, client, usuario_prof1, usuario_prof2,
                                  profesor1, profesor2, uea, periodo):
        # Prof1 crea una carta
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        client.post("/api/v1/cartas-tematicas/", carta_payload(uea.id, periodo.id), format="json")

        # Prof2 no debe verla
        auth(client, "prof_doc2@cyad.uam.mx", "Prof1234!")
        r = client.get("/api/v1/cartas-tematicas/")
        assert r.status_code == 200
        assert r.data["count"] == 0

    def test_admin_ve_todas(self, client, admin, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        client.post("/api/v1/cartas-tematicas/", carta_payload(uea.id, periodo.id), format="json")

        auth(client, "admin_doc@cyad.uam.mx", "Admin1234!")
        r = client.get("/api/v1/cartas-tematicas/")
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_editar_propia(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        create_r = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id, periodo.id), format="json"
        )
        carta_id = create_r.data["id"]
        payload = carta_payload(uea.id, periodo.id)
        payload["objetivo_general"] = "Objetivo actualizado"
        r = client.put(f"/api/v1/cartas-tematicas/{carta_id}/", payload, format="json")
        assert r.status_code == 200
        assert r.data["objetivo_general"] == "Objetivo actualizado"

    def test_no_editar_ajena(self, client, usuario_prof1, usuario_prof2,
                              profesor1, profesor2, uea, periodo):
        # Prof1 crea
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        create_r = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id, periodo.id), format="json"
        )
        carta_id = create_r.data["id"]

        # Prof2 intenta editar — no debe encontrarla (queryset filtrado)
        auth(client, "prof_doc2@cyad.uam.mx", "Prof1234!")
        r = client.put(
            f"/api/v1/cartas-tematicas/{carta_id}/",
            carta_payload(uea.id, periodo.id),
            format="json",
        )
        assert r.status_code == 404

    def test_eliminar_borrador(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        create_r = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id, periodo.id), format="json"
        )
        r = client.delete(f"/api/v1/cartas-tematicas/{create_r.data['id']}/")
        assert r.status_code == 204

    def test_no_eliminar_enviado(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        create_r = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id, periodo.id), format="json"
        )
        carta_id = create_r.data["id"]
        # Cambiar a ENVIADO
        client.post(f"/api/v1/cartas-tematicas/{carta_id}/cambiar-estado/",
                    {"estado": "ENVIADO"}, format="json")
        r = client.delete(f"/api/v1/cartas-tematicas/{carta_id}/")
        assert r.status_code == 400

    def test_no_editar_enviado(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        create_r = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id, periodo.id), format="json"
        )
        carta_id = create_r.data["id"]
        client.post(f"/api/v1/cartas-tematicas/{carta_id}/cambiar-estado/",
                    {"estado": "ENVIADO"}, format="json")
        payload = carta_payload(uea.id, periodo.id)
        payload["objetivo_general"] = "Intento de modificación"
        r = client.put(f"/api/v1/cartas-tematicas/{carta_id}/", payload, format="json")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Unicidad
# ---------------------------------------------------------------------------

class TestUnicidad:
    def test_duplicado_bloqueado(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        client.post("/api/v1/cartas-tematicas/", carta_payload(uea.id, periodo.id), format="json")
        r = client.post(
            "/api/v1/cartas-tematicas/",
            carta_payload(uea.id, periodo.id),
            format="json",
        )
        assert r.status_code == 400  # UniqueConstraint violado

    def test_distinto_grupo_permitido(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        client.post("/api/v1/cartas-tematicas/", carta_payload(uea.id, periodo.id, id_grupo="G01"), format="json")
        r = client.post(
            "/api/v1/cartas-tematicas/",
            carta_payload(uea.id, periodo.id, id_grupo="G02"),
            format="json",
        )
        assert r.status_code == 201


# ---------------------------------------------------------------------------
# Requisito de Recuperación
# ---------------------------------------------------------------------------

class TestRequisitoRecuperacion:
    def test_crear_requisito(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        r = client.post(
            "/api/v1/requisitos-recuperacion/",
            {
                "uea": uea.id,
                "periodo": periodo.id,
                "nombre_grupo": "Grupo RR",
                "id_grupo": "G01",
                "horario": "Martes 14-16",
                "espacio_modalidad": "PRESENCIAL",
                "indicaciones": "Entregar proyecto final.",
                "items": [
                    {"orden": 1, "descripcion": "Entregar reporte escrito"},
                    {"orden": 2, "descripcion": "Presentación oral"},
                ],
            },
            format="json",
        )
        assert r.status_code == 201
        assert len(r.data["items"]) == 2

    def test_admin_solo_lectura_requisito(self, client, admin, usuario_prof1,
                                          profesor1, uea, periodo):
        # Admin intenta crear directamente (no tiene perfil de profesor)
        auth(client, "admin_doc@cyad.uam.mx", "Admin1234!")
        r = client.post(
            "/api/v1/requisitos-recuperacion/",
            {
                "uea": uea.id, "periodo": periodo.id,
                "nombre_grupo": "Admin Group", "id_grupo": "G99",
                "horario": "Viernes 10-12",
            },
            format="json",
        )
        assert r.status_code == 403

    def test_cambiar_estado(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        create_r = client.post(
            "/api/v1/requisitos-recuperacion/",
            {
                "uea": uea.id, "periodo": periodo.id,
                "nombre_grupo": "G Estado", "id_grupo": "G10",
                "horario": "Miércoles 9-11", "indicaciones": "...",
            },
            format="json",
        )
        r_id = create_r.data["id"]
        r = client.post(
            f"/api/v1/requisitos-recuperacion/{r_id}/cambiar-estado/",
            {"estado": "PUBLICADO"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["estado"] == "PUBLICADO"
