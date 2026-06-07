"""Tests de documentos académicos (Carta Temática + Requisitos de Recuperación).

Tras el rediseño de junio 2026:
- Documentos planos con campos de texto libre, sin sub-modelos.
- Vista pública sin auth para documentos PUBLICADOS.
"""

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
    return UEA.objects.create(
        clave="1403001D", nombre="Diseño de Objetos I",
        licenciatura=licenciatura,
        liga="https://cyad.azc.uam.mx/uea/1403001",
    )


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


# Payload mínimo con los nuevos campos planos
def carta_payload(uea_id, id_grupo="G01", **extra):
    """`periodo` se asigna en backend, no se envía."""
    p = {
        "uea": uea_id,
        "nombre_grupo": "Grupo Test",
        "id_grupo": id_grupo,
        "horario": "Lunes 10-12",
        "modalidad": "PRESENCIAL",
        "descripcion_uea": "UEA de prueba.",
        "objetivo_general": "Objetivo de prueba",
        "objetivos_particulares": "Op1, Op2",
        "contenido_sintetico": "Contenido X",
        "objetivos_aprendizaje": "OA1",
        "requerimientos": "Lápices",
        "conocimientos_previos": "Dibujo",
        "modalidad_evaluacion": "Examen final 100%",
        "revisiones_asesorias": "Viernes 4-5",
        "bibliografia": "Autor, A. (2024). Libro.",
        "calendarizacion_actividades": "Semana 1: intro",
    }
    p.update(extra)
    return p


def requisito_payload(uea_id, id_grupo="G01", **extra):
    p = {
        "uea": uea_id,
        "nombre_grupo": "Grupo RR",
        "id_grupo": id_grupo,
        "horario": "Martes 14-16",
        "lugar": "Aula H-204",
        "duracion_aprox": "2 horas",
        "fecha_hora": "Lunes 15 de mayo, 10:00 h",
        "recursos_necesarios": "Papel, cartulina",
        "requisitos": "Maqueta + investigación",
        "notas": "Sin retardos",
    }
    p.update(extra)
    return p


# ---------------------------------------------------------------------------
# Carta Temática — CRUD
# ---------------------------------------------------------------------------

class TestCartaTematicaCRUD:
    def test_crear_carta(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        r = client.post(
            "/api/v1/cartas-tematicas/",
            carta_payload(uea.id),
            format="json",
        )
        assert r.status_code == 201, r.data
        assert r.data["estado"] == "BORRADOR"
        assert r.data["profesor_nombre"] == "Profesor Doc 1"
        # Campos nuevos persisten
        assert r.data["descripcion_uea"] == "UEA de prueba."
        assert r.data["modalidad_evaluacion"] == "Examen final 100%"
        assert r.data["bibliografia"].startswith("Autor")
        # Periodo se auto-asigna desde el activo para Cartas
        assert r.data["periodo"] == periodo.id

    def test_listar_solo_propias(self, client, usuario_prof1, usuario_prof2,
                                  profesor1, profesor2, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        client.post("/api/v1/cartas-tematicas/", carta_payload(uea.id), format="json")
        auth(client, "prof_doc2@cyad.uam.mx", "Prof1234!")
        r = client.get("/api/v1/cartas-tematicas/")
        assert r.status_code == 200
        results = r.data.get("results", r.data)
        assert len(results) == 0

    def test_admin_ve_todas(self, client, admin, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        client.post("/api/v1/cartas-tematicas/", carta_payload(uea.id), format="json")
        auth(client, "admin_doc@cyad.uam.mx", "Admin1234!")
        r = client.get("/api/v1/cartas-tematicas/")
        assert r.status_code == 200
        results = r.data.get("results", r.data)
        assert len(results) >= 1

    def test_editar_propia(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        c = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id), format="json",
        )
        payload = carta_payload(uea.id)
        payload["objetivo_general"] = "Editado"
        r = client.put(f"/api/v1/cartas-tematicas/{c.data['id']}/", payload, format="json")
        assert r.status_code == 200, r.data
        assert r.data["objetivo_general"] == "Editado"

    def test_no_editar_ajena(self, client, usuario_prof1, usuario_prof2,
                              profesor1, profesor2, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        c = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id), format="json",
        )
        auth(client, "prof_doc2@cyad.uam.mx", "Prof1234!")
        r = client.put(
            f"/api/v1/cartas-tematicas/{c.data['id']}/",
            carta_payload(uea.id),
            format="json",
        )
        # 404 si el queryset filtra por propietario; 403 si el permission objet
        assert r.status_code in (403, 404)

    def test_eliminar_borrador(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        c = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id), format="json",
        )
        r = client.delete(f"/api/v1/cartas-tematicas/{c.data['id']}/")
        assert r.status_code == 204

    def test_no_eliminar_publicado(self, client, usuario_prof1, profesor1, uea, periodo):
        """Una carta PUBLICADA no se puede eliminar directamente — hay que
        despublicarla primero (el frontend lo hace automático)."""
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        c = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id), format="json",
        )
        cid = c.data["id"]
        client.post(f"/api/v1/cartas-tematicas/{cid}/cambiar-estado/",
                    {"estado": "PUBLICADO"}, format="json")
        r = client.delete(f"/api/v1/cartas-tematicas/{cid}/")
        assert r.status_code == 400

    def test_profesor_oculta_periodo_inactivo(self, client, usuario_prof1, profesor1, uea, periodo):
        """El profesor NO debe ver sus cartas de periodos sin activo_cartas=True."""
        from catalogos.models import Periodo
        from documentos.models import CartaTematica
        # Periodo viejo, inactivo para cartas
        periodo_viejo = Periodo.objects.create(
            clave="25-OLD",
            fecha_inicio="2025-01-01",
            fecha_fin="2025-04-30",
            # Sin flags activos
        )
        # Una carta vieja directamente en DB (sin pasar por la API)
        CartaTematica.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo_viejo,
            nombre_grupo="VIEJO", id_grupo="VIEJO", horario="L 10-12",
        )
        # Una carta del periodo actual (activo)
        CartaTematica.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo,
            nombre_grupo="HOY", id_grupo="HOY-1", horario="L 10-12",
        )
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        r = client.get("/api/v1/cartas-tematicas/")
        assert r.status_code == 200
        results = r.data.get("results", r.data)
        # Solo debe aparecer la del periodo activo
        ids_grupo = [c["id_grupo"] for c in results]
        assert "HOY-1" in ids_grupo
        assert "VIEJO" not in ids_grupo

    def test_admin_ve_todos_los_periodos(self, client, admin, usuario_prof1, profesor1, uea, periodo):
        """El admin sí ve las cartas de cualquier periodo."""
        from catalogos.models import Periodo
        from documentos.models import CartaTematica
        periodo_viejo = Periodo.objects.create(
            clave="25-OLD-A",
            fecha_inicio="2025-01-01",
            fecha_fin="2025-04-30",
        )
        CartaTematica.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo_viejo,
            nombre_grupo="VIEJO-A", id_grupo="VIEJO-A", horario="L 10-12",
        )
        auth(client, "admin_doc@cyad.uam.mx", "Admin1234!")
        r = client.get("/api/v1/cartas-tematicas/")
        assert r.status_code == 200
        results = r.data.get("results", r.data)
        ids_grupo = [c["id_grupo"] for c in results]
        assert "VIEJO-A" in ids_grupo

    def test_estado_enviado_no_existe(self, client, usuario_prof1, profesor1, uea, periodo):
        """Tras retirar ENVIADO de las choices, el cambio a ENVIADO debe rechazarse."""
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        c = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id), format="json",
        )
        cid = c.data["id"]
        r = client.post(f"/api/v1/cartas-tematicas/{cid}/cambiar-estado/",
                        {"estado": "ENVIADO"}, format="json")
        assert r.status_code == 400

    def test_no_editar_publicado_debe_despublicar(self, client, usuario_prof1, profesor1, uea, periodo):
        """Una carta PUBLICADA no se puede editar. Hay que despublicarla primero."""
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        c = client.post(
            "/api/v1/cartas-tematicas/", carta_payload(uea.id), format="json",
        )
        cid = c.data["id"]
        # Pasamos a PUBLICADO
        client.post(f"/api/v1/cartas-tematicas/{cid}/cambiar-estado/",
                    {"estado": "PUBLICADO"}, format="json")
        # Intentar editar → 400
        r = client.put(f"/api/v1/cartas-tematicas/{cid}/",
                       carta_payload(uea.id), format="json")
        assert r.status_code == 400
        assert "Despublica" in str(r.data)
        # Despublicar (regresar a BORRADOR) → 200
        r2 = client.post(f"/api/v1/cartas-tematicas/{cid}/cambiar-estado/",
                         {"estado": "BORRADOR"}, format="json")
        assert r2.status_code == 200
        # Ahora sí podemos editar
        payload = carta_payload(uea.id)
        payload["objetivo_general"] = "Después de despublicar"
        r3 = client.put(f"/api/v1/cartas-tematicas/{cid}/", payload, format="json")
        assert r3.status_code == 200
        assert r3.data["objetivo_general"] == "Después de despublicar"


# ---------------------------------------------------------------------------
# Carta Temática — Unicidad
# ---------------------------------------------------------------------------

class TestUnicidad:
    def test_duplicado_bloqueado(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        client.post("/api/v1/cartas-tematicas/", carta_payload(uea.id), format="json")
        r = client.post(
            "/api/v1/cartas-tematicas/",
            carta_payload(uea.id),
            format="json",
        )
        assert r.status_code == 400

    def test_distinto_grupo_permitido(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        client.post(
            "/api/v1/cartas-tematicas/",
            carta_payload(uea.id, id_grupo="G01"),
            format="json",
        )
        r = client.post(
            "/api/v1/cartas-tematicas/",
            carta_payload(uea.id, id_grupo="G02"),
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
            requisito_payload(uea.id),
            format="json",
        )
        assert r.status_code == 201, r.data
        assert r.data["lugar"] == "Aula H-204"
        assert r.data["fecha_hora"] == "Lunes 15 de mayo, 10:00 h"
        assert r.data["requisitos"] == "Maqueta + investigación"
        assert r.data["periodo"] == periodo.id

    def test_admin_solo_lectura_requisito(self, client, admin, usuario_prof1,
                                          profesor1, uea, periodo):
        auth(client, "admin_doc@cyad.uam.mx", "Admin1234!")
        r = client.post(
            "/api/v1/requisitos-recuperacion/",
            requisito_payload(uea.id, id_grupo="G99"),
            format="json",
        )
        assert r.status_code == 403

    def test_cambiar_estado(self, client, usuario_prof1, profesor1, uea, periodo):
        auth(client, "prof_doc1@cyad.uam.mx", "Prof1234!")
        c = client.post(
            "/api/v1/requisitos-recuperacion/",
            requisito_payload(uea.id, id_grupo="G10"),
            format="json",
        )
        r_id = c.data["id"]
        r = client.post(
            f"/api/v1/requisitos-recuperacion/{r_id}/cambiar-estado/",
            {"estado": "PUBLICADO"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["estado"] == "PUBLICADO"


# ---------------------------------------------------------------------------
# Vista pública (sin auth)
# ---------------------------------------------------------------------------

class TestPublicCarta:
    def test_carta_publicada_visible_sin_auth(self, client, usuario_prof1, profesor1, uea, periodo):
        """Una Carta PUBLICADA se puede consultar sin autenticación."""
        carta = CartaTematica.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo,
            nombre_grupo="GP1", id_grupo="GPID", horario="Lun 10-12",
            descripcion_uea="Descripción pública",
            estado=CartaTematica.Estado.PUBLICADO,
        )
        # Cliente sin credentials
        r = APIClient().get(f"/api/v1/publico/cartas/{carta.id}/")
        assert r.status_code == 200
        assert r.data["tipo_documento"] == "Carta Temática"
        assert r.data["profesor_nombre"] == "Profesor Doc 1"
        assert r.data["profesor_correo"] == "prof_doc1@uam.mx"
        assert r.data["uea_clave"] == "1403001D"
        assert r.data["uea_liga"] == "https://cyad.azc.uam.mx/uea/1403001"
        assert r.data["descripcion_uea"] == "Descripción pública"

    def test_carta_borrador_no_visible(self, client, usuario_prof1, profesor1, uea, periodo):
        """Una carta en BORRADOR no aparece en el endpoint público."""
        carta = CartaTematica.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo,
            nombre_grupo="X", id_grupo="X", horario="X",
            estado=CartaTematica.Estado.BORRADOR,
        )
        r = APIClient().get(f"/api/v1/publico/cartas/{carta.id}/")
        assert r.status_code == 404

    def test_carta_oculta_datos_sensibles(self, client, usuario_prof1, profesor1, uea, periodo):
        """La respuesta pública no expone IDs internos del usuario."""
        carta = CartaTematica.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo,
            nombre_grupo="X", id_grupo="Y", horario="Z",
            estado=CartaTematica.Estado.PUBLICADO,
        )
        r = APIClient().get(f"/api/v1/publico/cartas/{carta.id}/")
        assert r.status_code == 200
        # Solo campos seguros: nombre y correo institucional, nada de usuario.id
        keys = set(r.data.keys())
        assert "profesor" not in keys  # no el FK id raw
        assert "usuario" not in keys


class TestPublicListados:
    """Listados públicos para la home (sin auth)."""

    def test_lista_cartas_publicas_filtro_lic(self, client, usuario_prof1, profesor1, uea, periodo):
        # Una carta PUBLICADA en la UEA/licenciatura del fixture
        CartaTematica.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo,
            nombre_grupo="GP1", id_grupo="GP1-ID", horario="Lun 10-12",
            estado=CartaTematica.Estado.PUBLICADO,
        )
        # Una en BORRADOR — no debe aparecer en la pública
        CartaTematica.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo,
            nombre_grupo="HID", id_grupo="HID-ID", horario="Lun 10-12",
            estado=CartaTematica.Estado.BORRADOR,
        )
        r = APIClient().get(f"/api/v1/publico/cartas/?licenciatura={uea.licenciatura_id}")
        assert r.status_code == 200
        # Sin pagination_class → respuesta es lista directa
        ids_grupo = [c["id_grupo"] for c in r.data]
        assert "GP1-ID" in ids_grupo
        assert "HID-ID" not in ids_grupo

    def test_lista_cartas_publicas_filtro_uea(self, client, usuario_prof1, profesor1, uea, periodo):
        CartaTematica.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo,
            nombre_grupo="A", id_grupo="UEA-A", horario="Lun 10-12",
            estado=CartaTematica.Estado.PUBLICADO,
        )
        r = APIClient().get(f"/api/v1/publico/cartas/?uea={uea.id}")
        assert r.status_code == 200
        assert len(r.data) >= 1
        assert all(c["uea_clave"] == uea.clave for c in r.data)

    def test_lista_requisitos_publicas(self, client, usuario_prof1, profesor1, uea, periodo):
        RequisitoRecuperacion.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo,
            nombre_grupo="RR", id_grupo="RR-1", horario="Mar 9-11",
            estado=RequisitoRecuperacion.Estado.PUBLICADO,
        )
        r = APIClient().get(f"/api/v1/publico/requisitos/?uea={uea.id}")
        assert r.status_code == 200
        assert len(r.data) >= 1


class TestPublicRequisito:
    def test_requisito_publicado_visible(self, client, usuario_prof1, profesor1, uea, periodo):
        rr = RequisitoRecuperacion.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo,
            nombre_grupo="GP2", id_grupo="GP2", horario="Mar 9-11",
            lugar="Aula 1", requisitos="Maqueta",
            estado=RequisitoRecuperacion.Estado.PUBLICADO,
        )
        r = APIClient().get(f"/api/v1/publico/requisitos/{rr.id}/")
        assert r.status_code == 200
        assert r.data["tipo_documento"] == "Evaluación de Recuperación"
        assert r.data["lugar"] == "Aula 1"
        assert r.data["requisitos"] == "Maqueta"

    def test_requisito_borrador_no_visible(self, client, usuario_prof1, profesor1, uea, periodo):
        rr = RequisitoRecuperacion.objects.create(
            profesor=profesor1, uea=uea, periodo=periodo,
            nombre_grupo="X", id_grupo="X", horario="X",
            estado=RequisitoRecuperacion.Estado.BORRADOR,
        )
        r = APIClient().get(f"/api/v1/publico/requisitos/{rr.id}/")
        assert r.status_code == 404
