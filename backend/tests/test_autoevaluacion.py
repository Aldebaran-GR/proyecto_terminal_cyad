"""Tests del módulo Autoevaluación (M4 + scoring + versionado)."""

import pytest
from rest_framework.test import APIClient

from accounts.models import Profesor, Usuario
from autoevaluacion.models import (
    Formulario,
    NivelDesempeno,
    OpcionPregunta,
    Pregunta,
    Respuesta,
    RespuestaPregunta,
    Seccion,
)
from catalogos.models import Departamento, Periodo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin(db):
    return Usuario.objects.create_user(
        email="admin_ae@cyad.uam.mx",
        nombre="Admin AE",
        password="Admin1234!",
        rol=Usuario.Rol.ADMIN,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def usuario_prof(db):
    return Usuario.objects.create_user(
        email="prof_ae@cyad.uam.mx",
        nombre="Profesor AE",
        password="Prof1234!",
        rol=Usuario.Rol.PROFESOR,
    )


@pytest.fixture
def usuario_prof2(db):
    return Usuario.objects.create_user(
        email="prof_ae2@cyad.uam.mx",
        nombre="Profesor AE 2",
        password="Prof1234!",
        rol=Usuario.Rol.PROFESOR,
    )


@pytest.fixture
def depto(db):
    return Departamento.objects.create(clave="EDTAE", nombre="Evaluación AE")


@pytest.fixture
def periodo(db):
    return Periodo.objects.create(
        clave="26-IAE",
        fecha_inicio="2026-01-12",
        fecha_fin="2026-04-17",
        activo_autoevaluacion=True,
    )


@pytest.fixture
def profesor(db, usuario_prof, depto):
    return Profesor.objects.create(
        usuario=usuario_prof,
        nombre_completo="Profesor AE",
        correo_institucional="prof_ae@uam.mx",
        departamento=depto,
    )


@pytest.fixture
def profesor2(db, usuario_prof2, depto):
    return Profesor.objects.create(
        usuario=usuario_prof2,
        nombre_completo="Profesor AE 2",
        correo_institucional="prof_ae2@uam.mx",
        departamento=depto,
    )


def auth_admin(client):
    r = client.post(
        "/api/v1/auth/login/",
        {"email": "admin_ae@cyad.uam.mx", "password": "Admin1234!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


def auth_prof(client):
    r = client.post(
        "/api/v1/auth/login/",
        {"email": "prof_ae@cyad.uam.mx", "password": "Prof1234!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


def auth_prof2(client):
    r = client.post(
        "/api/v1/auth/login/",
        {"email": "prof_ae2@cyad.uam.mx", "password": "Prof1234!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


def make_formulario(periodo, admin_user=None):
    return Formulario.objects.create(
        titulo="Autoevaluación Trimestral",
        descripcion="Evaluación de desempeño docente",
        periodo=periodo,
        created_by=admin_user,
    )


def make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, orden=1, obligatoria=True):
    return Pregunta.objects.create(
        formulario=formulario,
        tipo=tipo,
        texto=f"Pregunta {orden}",
        obligatoria=obligatoria,
        orden=orden,
    )


def make_opcion(pregunta, texto, orden=1, puntos=0):
    return OpcionPregunta.objects.create(
        pregunta=pregunta, texto=texto, orden=orden, puntos=puntos
    )


def make_nivel(formulario, nombre, pmin, pmax, observacion="Obs.", color="gray", orden=0):
    return NivelDesempeno.objects.create(
        formulario=formulario,
        nombre=nombre,
        porcentaje_min=pmin,
        porcentaje_max=pmax,
        observacion=observacion,
        color=color,
        orden=orden,
    )


# ---------------------------------------------------------------------------
# Admin — CRUD Formulario
# ---------------------------------------------------------------------------


class TestFormularioCRUD:
    def test_admin_crea_formulario(self, client, admin, periodo):
        auth_admin(client)
        r = client.post(
            "/api/v1/formularios/",
            {"titulo": "Autoevaluación Q1", "descripcion": "Desc", "periodo": periodo.id},
            format="json",
        )
        assert r.status_code == 201
        assert r.data["estado"] == "BORRADOR"
        assert r.data["version"] == 1
        assert r.data["created_by"] == admin.id

    def test_profesor_no_puede_crear_formulario(self, client, admin, usuario_prof, profesor, periodo):
        auth_prof(client)
        r = client.post(
            "/api/v1/formularios/",
            {"titulo": "X", "periodo": periodo.id},
            format="json",
        )
        assert r.status_code == 403

    def test_admin_lista_formularios(self, client, admin, periodo):
        auth_admin(client)
        make_formulario(periodo, admin)
        r = client.get("/api/v1/formularios/")
        assert r.status_code == 200
        assert r.data["count"] >= 1

    def test_admin_edita_formulario(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.patch(
            f"/api/v1/formularios/{formulario.id}/",
            {"titulo": "Título actualizado"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["titulo"] == "Título actualizado"

    def test_admin_elimina_formulario_borrador(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.delete(f"/api/v1/formularios/{formulario.id}/")
        assert r.status_code == 204


# ---------------------------------------------------------------------------
# Admin — Publicar / Cerrar / Publicar revisión
# ---------------------------------------------------------------------------


class TestFormularioEstados:
    def test_publicar_formulario(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 200
        assert r.data["estado"] == "PUBLICADO"
        assert r.data["version"] == 1

    def test_no_publicar_ya_publicado(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        formulario.publicar()
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 400

    def test_cerrar_formulario(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        formulario.publicar()
        r = client.post(f"/api/v1/formularios/{formulario.id}/cerrar/")
        assert r.status_code == 200
        assert r.data["estado"] == "CERRADO"

    def test_no_cerrar_borrador(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(f"/api/v1/formularios/{formulario.id}/cerrar/")
        assert r.status_code == 400

    def test_publicar_revision_incrementa_version(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        formulario.publicar()
        formulario.cerrar()
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar-revision/")
        assert r.status_code == 200
        assert r.data["version"] == 2
        assert r.data["estado"] == "PUBLICADO"

    def test_publicar_revision_requiere_cerrado(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        # BORRADOR → no debería funcionar
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar-revision/")
        assert r.status_code == 400

    def test_despublicar_formulario(self, client, admin, periodo):
        """PUBLICADO → BORRADOR vía /despublicar/, conservando versión."""
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        formulario.publicar()
        assert formulario.estado == "PUBLICADO"
        r = client.post(f"/api/v1/formularios/{formulario.id}/despublicar/")
        assert r.status_code == 200, r.data
        assert r.data["estado"] == "BORRADOR"
        formulario.refresh_from_db()
        assert formulario.estado == "BORRADOR"
        # La versión no se incrementa al despublicar
        assert formulario.version == 1

    def test_no_despublicar_borrador(self, client, admin, periodo):
        """Despublicar un BORRADOR no tiene sentido → 400."""
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(f"/api/v1/formularios/{formulario.id}/despublicar/")
        assert r.status_code == 400

    def test_no_editar_pregunta_formulario_publicado(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        pregunta = make_pregunta(formulario)
        formulario.publicar()
        r = client.patch(
            f"/api/v1/preguntas/{pregunta.id}/",
            {"texto": "Texto modificado"},
            format="json",
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Admin — Preguntas y Secciones
# ---------------------------------------------------------------------------


class TestPreguntasCRUD:
    def test_admin_crea_pregunta_texto(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(
            "/api/v1/preguntas/",
            {
                "formulario": formulario.id,
                "tipo": "TEXTO_CORTO",
                "texto": "¿Cómo evalúas tu desempeño?",
                "obligatoria": True,
                "orden": 1,
            },
            format="json",
        )
        assert r.status_code == 201
        assert r.data["tipo"] == "TEXTO_CORTO"

    def test_admin_crea_pregunta_con_opciones_y_puntos(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(
            "/api/v1/preguntas/",
            {
                "formulario": formulario.id,
                "tipo": "OPCION_UNICA",
                "texto": "Selecciona una opción",
                "obligatoria": True,
                "orden": 1,
                "opciones": [
                    {"texto": "Excelente", "valor": "3", "puntos": 3, "orden": 1},
                    {"texto": "Bueno",     "valor": "2", "puntos": 2, "orden": 2},
                    {"texto": "Regular",   "valor": "1", "puntos": 1, "orden": 3},
                ],
            },
            format="json",
        )
        assert r.status_code == 201
        assert len(r.data["opciones"]) == 3
        # Verificar que se guardaron los puntos
        assert float(r.data["opciones"][0]["puntos"]) == 3.0

    def test_admin_crea_seccion(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(
            "/api/v1/secciones/",
            {"formulario": formulario.id, "titulo": "Sección 1", "orden": 1},
            format="json",
        )
        assert r.status_code == 201


# ---------------------------------------------------------------------------
# Admin — Niveles de desempeño
# ---------------------------------------------------------------------------


class TestNivelDesempeno:
    def test_admin_crea_nivel(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(
            "/api/v1/niveles-desempeno/",
            {
                "formulario": formulario.id,
                "nombre": "Excelente",
                "porcentaje_min": "90.00",
                "porcentaje_max": "100.00",
                "observacion": "Desempeño sobresaliente.",
                "color": "green",
                "orden": 1,
            },
            format="json",
        )
        assert r.status_code == 201
        assert r.data["nombre"] == "Excelente"

    def test_nivel_invalido_min_mayor_max(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(
            "/api/v1/niveles-desempeno/",
            {
                "formulario": formulario.id,
                "nombre": "Inválido",
                "porcentaje_min": "80.00",
                "porcentaje_max": "50.00",
                "observacion": "Mal.",
                "color": "red",
            },
            format="json",
        )
        assert r.status_code == 400

    def test_niveles_incluidos_en_formulario(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        make_nivel(formulario, "Excelente", 90, 100, color="green", orden=1)
        make_nivel(formulario, "Regular", 50, 89, color="yellow", orden=2)
        r = client.get(f"/api/v1/formularios/{formulario.id}/")
        assert r.status_code == 200
        assert len(r.data["niveles"]) == 2

    def test_profesor_no_puede_crear_nivel(self, client, admin, usuario_prof, profesor, periodo):
        auth_prof(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(
            "/api/v1/niveles-desempeno/",
            {
                "formulario": formulario.id,
                "nombre": "Intento",
                "porcentaje_min": "0.00",
                "porcentaje_max": "100.00",
                "observacion": "Hack.",
            },
            format="json",
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Profesor — Formularios disponibles
# ---------------------------------------------------------------------------


class TestFormulariosDisponibles:
    def test_profesor_ve_formularios_publicados(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        formulario.publicar()
        auth_prof(client)
        r = client.get("/api/v1/formularios-disponibles/")
        assert r.status_code == 200
        assert r.data["count"] == 1
        # Opciones sin campo puntos para el profesor
        assert "puntaje_maximo_posible" in r.data["results"][0]

    def test_profesor_no_ve_borradores(self, client, admin, usuario_prof, profesor, periodo):
        make_formulario(periodo, admin)  # BORRADOR
        auth_prof(client)
        r = client.get("/api/v1/formularios-disponibles/")
        assert r.status_code == 200
        assert r.data["count"] == 0

    def test_admin_no_accede_formularios_disponibles(self, client, admin, periodo):
        auth_admin(client)
        r = client.get("/api/v1/formularios-disponibles/")
        assert r.status_code == 403

    def test_profesor_no_ve_formularios_de_periodo_inactivo(
        self, client, admin, usuario_prof, profesor, periodo,
    ):
        """Formularios PUBLICADOS de un periodo SIN activo_autoevaluacion=True
        no deben aparecer al profesor (trimestres pasados ocultos)."""
        periodo_viejo = Periodo.objects.create(
            clave="25-OLDAE",
            fecha_inicio="2025-01-01",
            fecha_fin="2025-04-30",
            # Sin activo_autoevaluacion=True
        )
        formulario_viejo = make_formulario(periodo_viejo, admin)
        formulario_viejo.publicar()
        # Formulario del periodo actual (con activo_autoevaluacion=True por fixture)
        formulario_actual = make_formulario(periodo, admin)
        formulario_actual.publicar()
        auth_prof(client)
        r = client.get("/api/v1/formularios-disponibles/")
        assert r.status_code == 200
        # Solo el del periodo activo
        ids = [f["id"] for f in r.data["results"]]
        assert formulario_actual.id in ids
        assert formulario_viejo.id not in ids


# ---------------------------------------------------------------------------
# Profesor — Responder formulario
# ---------------------------------------------------------------------------


class TestResponderFormulario:
    def test_profesor_crea_respuesta_borrador(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        formulario.publicar()
        auth_prof(client)
        r = client.post(
            "/api/v1/respuestas/",
            {"formulario": formulario.id},
            format="json",
        )
        assert r.status_code == 201
        assert r.data["estado"] == "BORRADOR"
        assert r.data["version_formulario"] == 1

    def test_no_responder_formulario_cerrado(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        formulario.publicar()
        formulario.cerrar()
        auth_prof(client)
        r = client.post(
            "/api/v1/respuestas/",
            {"formulario": formulario.id},
            format="json",
        )
        assert r.status_code == 400

    def test_no_duplicar_respuesta_misma_version(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        formulario.publicar()
        auth_prof(client)
        client.post("/api/v1/respuestas/", {"formulario": formulario.id}, format="json")
        r = client.post("/api/v1/respuestas/", {"formulario": formulario.id}, format="json")
        assert r.status_code == 400

    def test_profesor_envia_respuesta(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO)
        formulario.publicar()
        auth_prof(client)
        create_r = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [{"pregunta": pregunta.id, "valor_texto": "Muy bien"}],
            },
            format="json",
        )
        r_id = create_r.data["id"]
        r = client.post(f"/api/v1/respuestas/{r_id}/enviar/")
        assert r.status_code == 200
        assert r.data["estado"] == "ENVIADO"

    def test_envio_falla_sin_obligatorias(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, obligatoria=True)
        formulario.publicar()
        auth_prof(client)
        create_r = client.post(
            "/api/v1/respuestas/",
            {"formulario": formulario.id},
            format="json",
        )
        r_id = create_r.data["id"]
        r = client.post(f"/api/v1/respuestas/{r_id}/enviar/")
        assert r.status_code == 400

    def test_no_modificar_respuesta_enviada(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO)
        formulario.publicar()
        auth_prof(client)
        create_r = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [{"pregunta": pregunta.id, "valor_texto": "Ok"}],
            },
            format="json",
        )
        r_id = create_r.data["id"]
        client.post(f"/api/v1/respuestas/{r_id}/enviar/")
        r = client.patch(
            f"/api/v1/respuestas/{r_id}/",
            {"items": [{"pregunta": pregunta.id, "valor_texto": "Intento modificar"}]},
            format="json",
        )
        assert r.status_code == 400

    def test_profesor2_no_ve_respuesta_de_prof1(
        self, client, admin, usuario_prof, usuario_prof2, profesor, profesor2, periodo
    ):
        formulario = make_formulario(periodo, admin)
        formulario.publicar()
        auth_prof(client)
        create_r = client.post(
            "/api/v1/respuestas/",
            {"formulario": formulario.id},
            format="json",
        )
        r_id = create_r.data["id"]
        auth_prof2(client)
        r = client.get(f"/api/v1/respuestas/{r_id}/")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Versionado — responder nueva versión tras publicar_revision
# ---------------------------------------------------------------------------


class TestVersionadoFormulario:
    def test_ya_respondido_false_tras_nueva_version(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Tras publicar_revision, ya_respondido vuelve a False."""
        formulario = make_formulario(periodo, admin)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO)
        formulario.publicar()

        # Profesor responde y envía v1
        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {"formulario": formulario.id,
             "items": [{"pregunta": pregunta.id, "valor_texto": "V1"}]},
            format="json",
        )
        client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")

        # Admin cierra y publica nueva versión
        auth_admin(client)
        client.post(f"/api/v1/formularios/{formulario.id}/cerrar/")
        client.post(f"/api/v1/formularios/{formulario.id}/publicar-revision/")

        # Profesor comprueba formularios disponibles
        auth_prof(client)
        r = client.get("/api/v1/formularios-disponibles/")
        assert r.status_code == 200
        assert r.data["count"] == 1
        resultado = r.data["results"][0]
        assert resultado["version"] == 2
        assert resultado["ya_respondido"] is False
        assert resultado["respuesta_id"] is None

    def test_respuesta_v1_conservada_tras_nueva_version(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Las respuestas de la versión anterior no se eliminan."""
        formulario = make_formulario(periodo, admin)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO)
        formulario.publicar()

        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {"formulario": formulario.id,
             "items": [{"pregunta": pregunta.id, "valor_texto": "V1"}]},
            format="json",
        )
        client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")

        # Admin cierra y republica
        auth_admin(client)
        client.post(f"/api/v1/formularios/{formulario.id}/cerrar/")
        client.post(f"/api/v1/formularios/{formulario.id}/publicar-revision/")

        # La respuesta v1 sigue en la BD
        assert Respuesta.objects.filter(
            formulario=formulario, version_formulario=1
        ).count() == 1

    def test_profesor_puede_responder_nueva_version(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Profesor puede crear una nueva respuesta para la versión 2."""
        formulario = make_formulario(periodo, admin)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO)
        formulario.publicar()

        # Responde v1
        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {"formulario": formulario.id,
             "items": [{"pregunta": pregunta.id, "valor_texto": "V1"}]},
            format="json",
        )
        client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")

        # Admin publica v2
        auth_admin(client)
        client.post(f"/api/v1/formularios/{formulario.id}/cerrar/")
        client.post(f"/api/v1/formularios/{formulario.id}/publicar-revision/")

        # Profesor responde v2 sin conflicto de constraint
        auth_prof(client)
        r = client.post(
            "/api/v1/respuestas/",
            {"formulario": formulario.id,
             "items": [{"pregunta": pregunta.id, "valor_texto": "V2"}]},
            format="json",
        )
        assert r.status_code == 201
        assert r.data["version_formulario"] == 2


# ---------------------------------------------------------------------------
# Scoring — cálculo de puntaje al enviar
# ---------------------------------------------------------------------------


class TestScoringEnvio:
    def _crear_formulario_con_nivel(self, periodo, admin):
        """Formulario con 1 pregunta OPCION_UNICA (max 3 pts) y niveles."""
        formulario = make_formulario(periodo, admin)
        pregunta = Pregunta.objects.create(
            formulario=formulario,
            tipo=Pregunta.Tipo.OPCION_UNICA,
            texto="¿Cómo evalúas tu planeación?",
            obligatoria=True,
            orden=1,
        )
        op_alta = OpcionPregunta.objects.create(
            pregunta=pregunta, texto="Excelente", puntos=3, orden=1
        )
        OpcionPregunta.objects.create(
            pregunta=pregunta, texto="Regular", puntos=2, orden=2
        )
        OpcionPregunta.objects.create(
            pregunta=pregunta, texto="Deficiente", puntos=1, orden=3
        )
        make_nivel(formulario, "Excelente", 90, 100, color="green", orden=1)
        make_nivel(formulario, "Satisfactorio", 60, 89, color="blue", orden=2)
        make_nivel(formulario, "Deficiente", 0, 59, color="red", orden=3)
        formulario.publicar()
        return formulario, pregunta, op_alta

    def test_puntaje_opcion_unica_y_nivel(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        formulario, pregunta, op_alta = self._crear_formulario_con_nivel(periodo, admin)
        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [{
                    "pregunta": pregunta.id,
                    "opciones_seleccionadas": [op_alta.id],
                }],
            },
            format="json",
        )
        r = client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")
        assert r.status_code == 200
        assert float(r.data["puntaje_obtenido"]) == 3.0
        assert float(r.data["puntaje_maximo"]) == 3.0
        assert float(r.data["porcentaje"]) == 100.0
        assert r.data["nivel_desempeno"]["nombre"] == "Excelente"
        assert r.data["nivel_desempeno"]["color"] == "green"

    def test_puntaje_casillas_suma_seleccionadas(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        formulario = make_formulario(periodo, admin)
        pregunta = Pregunta.objects.create(
            formulario=formulario,
            tipo=Pregunta.Tipo.CASILLAS,
            texto="Selecciona las que aplican",
            obligatoria=True,
            orden=1,
        )
        op1 = OpcionPregunta.objects.create(pregunta=pregunta, texto="A", puntos=2, orden=1)
        op2 = OpcionPregunta.objects.create(pregunta=pregunta, texto="B", puntos=3, orden=2)
        OpcionPregunta.objects.create(pregunta=pregunta, texto="C", puntos=1, orden=3)
        formulario.publicar()

        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [{
                    "pregunta": pregunta.id,
                    "opciones_seleccionadas": [op1.id, op2.id],
                }],
            },
            format="json",
        )
        r = client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")
        assert r.status_code == 200
        # Seleccionó A(2) + B(3) = 5; máximo = A(2)+B(3)+C(1) = 6
        assert float(r.data["puntaje_obtenido"]) == 5.0
        assert float(r.data["puntaje_maximo"]) == 6.0
        assert round(float(r.data["porcentaje"]), 2) == round(5 / 6 * 100, 2)

    def test_texto_no_suma_puntaje(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Preguntas de texto no contribuyen al puntaje."""
        formulario = make_formulario(periodo, admin)
        make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, orden=1)
        formulario.publicar()

        auth_prof(client)
        pregunta = formulario.preguntas.first()
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [{"pregunta": pregunta.id, "valor_texto": "Respuesta abierta"}],
            },
            format="json",
        )
        r = client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")
        assert r.status_code == 200
        assert float(r.data["puntaje_obtenido"]) == 0.0
        assert float(r.data["puntaje_maximo"]) == 0.0
        assert r.data["nivel_desempeno"] is None

    def test_sin_nivel_si_porcentaje_no_cae_en_ningun_rango(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Si el porcentaje no coincide con ningún nivel, nivel_desempeno es None."""
        formulario = make_formulario(periodo, admin)
        pregunta = Pregunta.objects.create(
            formulario=formulario,
            tipo=Pregunta.Tipo.OPCION_UNICA,
            texto="Pregunta",
            obligatoria=True,
            orden=1,
        )
        op = OpcionPregunta.objects.create(pregunta=pregunta, texto="Opción", puntos=2, orden=1)
        # Solo define nivel para 80-100, la respuesta sacará 50%
        make_nivel(formulario, "Alto", 80, 100, color="green")
        formulario.publicar()

        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [{"pregunta": pregunta.id, "opciones_seleccionadas": [op.id]}],
            },
            format="json",
        )
        # puntaje_maximo = 2, obtenido = 2 → 100% → coincide con "Alto"
        # Para que no coincida, usamos pregunta con máx 4 pero opción de 2 pts (50%)
        # Recreamos con opción de 2 pts y otra de 4 pts (la seleccionada es la de 2)
        formulario2 = make_formulario(periodo, admin)
        p2 = Pregunta.objects.create(
            formulario=formulario2, tipo=Pregunta.Tipo.OPCION_UNICA,
            texto="P2", obligatoria=True, orden=1,
        )
        op_baja = OpcionPregunta.objects.create(pregunta=p2, texto="Baja", puntos=2, orden=1)
        OpcionPregunta.objects.create(pregunta=p2, texto="Alta", puntos=4, orden=2)
        # Nivel solo cubre 80-100; 50% no caerá en él
        make_nivel(formulario2, "Alto", 80, 100, color="green")
        formulario2.publicar()

        cr2 = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario2.id,
                "items": [{"pregunta": p2.id, "opciones_seleccionadas": [op_baja.id]}],
            },
            format="json",
        )
        r = client.post(f"/api/v1/respuestas/{cr2.data['id']}/enviar/")
        assert r.status_code == 200
        assert float(r.data["porcentaje"]) == 50.0
        assert r.data["nivel_desempeno"] is None

    def test_puntaje_maximo_posible_en_formulario(self, client, admin, periodo):
        """El formulario expone puntaje_maximo_posible calculado."""
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        pregunta = Pregunta.objects.create(
            formulario=formulario, tipo=Pregunta.Tipo.OPCION_UNICA,
            texto="P", obligatoria=True, orden=1,
        )
        OpcionPregunta.objects.create(pregunta=pregunta, texto="Alta", puntos=5, orden=1)
        OpcionPregunta.objects.create(pregunta=pregunta, texto="Baja", puntos=2, orden=2)
        r = client.get(f"/api/v1/formularios/{formulario.id}/")
        assert r.status_code == 200
        assert r.data["puntaje_maximo_posible"] == 5.0


# ---------------------------------------------------------------------------
# Admin — Estadísticas (actualizadas)
# ---------------------------------------------------------------------------


class TestEstadisticas:
    def test_estadisticas_formulario(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO)
        formulario.publicar()

        respuesta = Respuesta.objects.create(
            formulario=formulario, profesor=profesor, estado=Respuesta.Estado.ENVIADO
        )
        RespuestaPregunta.objects.create(
            respuesta=respuesta, pregunta=pregunta, valor_texto="Excelente"
        )

        auth_admin(client)
        r = client.get(f"/api/v1/formularios/{formulario.id}/estadisticas/")
        assert r.status_code == 200
        assert r.data["total_respuestas_enviadas"] == 1
        assert len(r.data["preguntas"]) == 1
        assert "distribucion_niveles" in r.data
        assert "puntable" in r.data["preguntas"][0]

    def test_estadisticas_con_escala_lineal(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.ESCALA_LINEAL)
        formulario.publicar()

        from accounts.models import Usuario as U
        for i in range(1, 4):
            u = U.objects.create_user(
                email=f"pstats{i}@uam.mx", nombre=f"P{i}", password="P1234!",
                rol=U.Rol.PROFESOR,
            )
            p = Profesor.objects.create(
                usuario=u,
                nombre_completo=f"P{i}",
                correo_institucional=f"pstats{i}@inst.mx",
                departamento=profesor.departamento,
            )
            resp = Respuesta.objects.create(
                formulario=formulario, profesor=p, estado=Respuesta.Estado.ENVIADO
            )
            RespuestaPregunta.objects.create(
                respuesta=resp, pregunta=pregunta, valor_texto=str(i + 2)
            )

        auth_admin(client)
        r = client.get(f"/api/v1/formularios/{formulario.id}/estadisticas/")
        assert r.status_code == 200
        assert r.data["preguntas"][0]["promedio"] is not None

    def test_estadisticas_solo_version_actual(self, client, admin, usuario_prof, profesor, periodo):
        """Las estadísticas filtran por versión; respuestas de v1 no aparecen en v2."""
        formulario = make_formulario(periodo, admin)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO)
        formulario.publicar()

        # Respuesta v1
        Respuesta.objects.create(
            formulario=formulario, profesor=profesor,
            estado=Respuesta.Estado.ENVIADO, version_formulario=1,
        )

        # Admin publica v2
        formulario.cerrar()
        formulario.publicar_revision()

        auth_admin(client)
        # Sin parámetro → usa versión actual (2)
        r = client.get(f"/api/v1/formularios/{formulario.id}/estadisticas/")
        assert r.status_code == 200
        assert r.data["version"] == 2
        assert r.data["total_respuestas_enviadas"] == 0

        # Con ?version=1 devuelve la de v1
        r2 = client.get(f"/api/v1/formularios/{formulario.id}/estadisticas/?version=1")
        assert r2.data["total_respuestas_enviadas"] == 1
