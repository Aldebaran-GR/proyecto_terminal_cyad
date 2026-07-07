"""Tests del módulo Autoevaluación (M4 + scoring + versionado)."""

import pytest
from rest_framework.test import APIClient

from accounts.models import Profesor, Usuario
from autoevaluacion.models import (
    FilaCuadricula,
    Formulario,
    NivelDesempeno,
    OpcionPregunta,
    Pregunta,
    Respuesta,
    RespuestaCelda,
    RespuestaPregunta,
    RespuestaSeccion,
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


def make_seccion(formulario, titulo="General", peso=100, orden=0):
    return Seccion.objects.create(
        formulario=formulario, titulo=titulo, peso=peso, orden=orden
    )


def make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, orden=1, obligatoria=True, seccion=None):
    return Pregunta.objects.create(
        formulario=formulario,
        tipo=tipo,
        texto=f"Pregunta {orden}",
        obligatoria=obligatoria,
        orden=orden,
        seccion=seccion,
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
        make_seccion(formulario, peso=100)
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 200
        assert r.data["estado"] == "PUBLICADO"
        assert r.data["version"] == 1

    def test_no_publicar_ya_publicado(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, peso=100)
        formulario.publicar()
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 400

    def test_cerrar_formulario(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, peso=100)
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
        make_seccion(formulario, peso=100)
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
        make_seccion(formulario, peso=100)
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
        seccion = make_seccion(formulario, peso=100)
        pregunta = make_pregunta(formulario, seccion=seccion)
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
        make_seccion(formulario, peso=100)
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
        no deben aparecer al profesor (trimestres pasados ocultos) — A MENOS
        que el profesor ya tenga una respuesta para consultar."""
        periodo_viejo = Periodo.objects.create(
            clave="25-OLDAE",
            fecha_inicio="2025-01-01",
            fecha_fin="2025-04-30",
            # Sin activo_autoevaluacion=True
        )
        formulario_viejo = make_formulario(periodo_viejo, admin)
        make_seccion(formulario_viejo, peso=100)
        formulario_viejo.publicar()
        # Formulario del periodo actual (con activo_autoevaluacion=True por fixture)
        formulario_actual = make_formulario(periodo, admin)
        make_seccion(formulario_actual, peso=100)
        formulario_actual.publicar()
        auth_prof(client)
        r = client.get("/api/v1/formularios-disponibles/")
        assert r.status_code == 200
        # Solo el del periodo activo
        ids = [f["id"] for f in r.data["results"]]
        assert formulario_actual.id in ids
        assert formulario_viejo.id not in ids

    def test_profesor_ve_historial_cuando_ya_respondio(
        self, client, admin, usuario_prof, profesor, periodo,
    ):
        """Si el profesor ya respondió un formulario, debe seguir viéndolo en
        la lista aunque el periodo del formulario ya no esté activo para AE
        — para que pueda consultar su resultado. La tarjeta debe traer
        `periodo_abierto=False` para que la UI sepa que es solo consulta.
        """
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, peso=100)
        formulario.publicar()
        # Profesor crea y envía respuesta con el periodo activo.
        Respuesta.objects.create(
            formulario=formulario,
            profesor=profesor,
            estado=Respuesta.Estado.ENVIADO,
            version_formulario=formulario.version,
        )
        # Admin cierra la autoevaluación del periodo.
        periodo.activo_autoevaluacion = False
        periodo.save(update_fields=["activo_autoevaluacion"])
        auth_prof(client)
        r = client.get("/api/v1/formularios-disponibles/")
        assert r.status_code == 200, r.data
        ids = [f["id"] for f in r.data["results"]]
        assert formulario.id in ids
        tarjeta = next(f for f in r.data["results"] if f["id"] == formulario.id)
        assert tarjeta["periodo_abierto"] is False
        assert tarjeta["ya_respondido"] is True

    def test_profesor_no_ve_historial_sin_respuesta(
        self, client, admin, usuario_prof, profesor, periodo,
    ):
        """Espejo del anterior: sin respuesta del profesor, un formulario de
        periodo inactivo NO aparece en la lista del profesor."""
        periodo.activo_autoevaluacion = False
        periodo.save(update_fields=["activo_autoevaluacion"])
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, peso=100)
        formulario.publicar()
        auth_prof(client)
        r = client.get("/api/v1/formularios-disponibles/")
        assert r.status_code == 200
        ids = [f["id"] for f in r.data["results"]]
        assert formulario.id not in ids


# ---------------------------------------------------------------------------
# Profesor — Responder formulario
# ---------------------------------------------------------------------------


class TestResponderFormulario:
    def test_profesor_crea_respuesta_borrador(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, peso=100)
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
        make_seccion(formulario, peso=100)
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
        make_seccion(formulario, peso=100)
        formulario.publicar()
        auth_prof(client)
        client.post("/api/v1/respuestas/", {"formulario": formulario.id}, format="json")
        r = client.post("/api/v1/respuestas/", {"formulario": formulario.id}, format="json")
        assert r.status_code == 400

    def test_profesor_envia_respuesta(self, client, admin, usuario_prof, profesor, periodo):
        formulario = make_formulario(periodo, admin)
        seccion = make_seccion(formulario, peso=100)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, seccion=seccion)
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
        seccion = make_seccion(formulario, peso=100)
        make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, obligatoria=True, seccion=seccion)
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
        seccion = make_seccion(formulario, peso=100)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, seccion=seccion)
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
        make_seccion(formulario, peso=100)
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
        seccion = make_seccion(formulario, peso=100)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, seccion=seccion)
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
        seccion = make_seccion(formulario, peso=100)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, seccion=seccion)
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
        seccion = make_seccion(formulario, peso=100)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, seccion=seccion)
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
        seccion = make_seccion(formulario, peso=100)
        pregunta = Pregunta.objects.create(
            formulario=formulario,
            seccion=seccion,
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
        seccion = make_seccion(formulario, peso=100)
        pregunta = Pregunta.objects.create(
            formulario=formulario,
            seccion=seccion,
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
        seccion = make_seccion(formulario, peso=100)
        make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, orden=1, seccion=seccion)
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
        seccion = make_seccion(formulario, peso=100)
        pregunta = Pregunta.objects.create(
            formulario=formulario,
            seccion=seccion,
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
        seccion2 = make_seccion(formulario2, peso=100)
        p2 = Pregunta.objects.create(
            formulario=formulario2, seccion=seccion2, tipo=Pregunta.Tipo.OPCION_UNICA,
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
        seccion = make_seccion(formulario, peso=100)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, seccion=seccion)
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
        seccion = make_seccion(formulario, peso=100)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.ESCALA_LINEAL, seccion=seccion)
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
        seccion = make_seccion(formulario, peso=100)
        make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, seccion=seccion)
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


# ---------------------------------------------------------------------------
# Gate por flag activo_autoevaluacion — bloquea create / enviar al profesor
# ---------------------------------------------------------------------------


class TestAutoevaluacionGatePeriodo:
    """Si el periodo deja de tener `activo_autoevaluacion=True`, el profesor
    pierde la capacidad de crear y enviar respuestas. El ciclo del Formulario
    (BORRADOR → PUBLICADO → CERRADO) se mantiene aparte.
    """

    def test_enviar_respuesta_bloqueado_si_flag_apagado(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, peso=100)
        formulario.publicar()
        # Profesor crea respuesta con el flag activo.
        auth_prof(client)
        r = client.post(
            "/api/v1/respuestas/", {"formulario": formulario.id}, format="json",
        )
        assert r.status_code == 201, r.data
        resp_id = r.data["id"]
        # Admin apaga el flag de autoevaluación.
        periodo.activo_autoevaluacion = False
        periodo.save(update_fields=["activo_autoevaluacion"])
        # Profesor intenta enviar → 400 con error en clave `periodo`.
        r = client.post(f"/api/v1/respuestas/{resp_id}/enviar/")
        assert r.status_code == 400
        assert "periodo" in str(r.data).lower()


# ---------------------------------------------------------------------------
# Gate por flag activo_autoevaluacion al CREAR un formulario (admin)
# ---------------------------------------------------------------------------


class TestGatePeriodoEnCreacionFormulario:
    """El admin solo puede crear/mover formularios a periodos habilitados para
    autoevaluación. Si el periodo no tiene `activo_autoevaluacion=True` y
    `estado=True`, la creación o el cambio de periodo deben rechazarse con 400.
    """

    def _periodo_inactivo(self):
        return Periodo.objects.create(
            clave="26-IIAE",
            fecha_inicio="2026-05-04",
            fecha_fin="2026-08-07",
            activo_autoevaluacion=False,
        )

    def test_admin_no_crea_formulario_con_periodo_inactivo(self, client, admin):
        auth_admin(client)
        periodo_off = self._periodo_inactivo()
        r = client.post(
            "/api/v1/formularios/",
            {"titulo": "AE bloqueada", "periodo": periodo_off.id},
            format="json",
        )
        assert r.status_code == 400, r.data
        assert "periodo" in r.data.get("errors", r.data)

    def test_admin_no_mueve_formulario_a_periodo_inactivo(
        self, client, admin, periodo
    ):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        periodo_off = self._periodo_inactivo()
        r = client.patch(
            f"/api/v1/formularios/{formulario.id}/",
            {"periodo": periodo_off.id},
            format="json",
        )
        assert r.status_code == 400, r.data
        assert "periodo" in r.data.get("errors", r.data)

    def test_admin_crea_formulario_con_periodo_activo(self, client, admin, periodo):
        auth_admin(client)
        r = client.post(
            "/api/v1/formularios/",
            {"titulo": "AE habilitada", "periodo": periodo.id},
            format="json",
        )
        assert r.status_code == 201, r.data
        assert r.data["estado"] == "BORRADOR"


# ---------------------------------------------------------------------------
# Ponderación por sección — validación de peso al publicar
# ---------------------------------------------------------------------------


class TestSeccionPeso:
    """PR2: Seccion.peso y _validar_estructura_para_publicar."""

    def test_crear_seccion_con_peso_valido(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(
            "/api/v1/secciones/",
            {"formulario": formulario.id, "titulo": "A", "peso": "60.00", "orden": 1},
            format="json",
        )
        assert r.status_code == 201
        assert float(r.data["peso"]) == 60.0

    def test_peso_negativo_rechazado(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(
            "/api/v1/secciones/",
            {"formulario": formulario.id, "titulo": "A", "peso": "-1", "orden": 1},
            format="json",
        )
        assert r.status_code == 400

    def test_peso_mayor_100_rechazado(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(
            "/api/v1/secciones/",
            {"formulario": formulario.id, "titulo": "A", "peso": "101", "orden": 1},
            format="json",
        )
        assert r.status_code == 400

    def test_publicar_falla_sin_secciones(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 400
        assert "sección" in str(r.data).lower() or "seccion" in str(r.data).lower()

    def test_publicar_falla_si_suma_distinta_de_100(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, titulo="A", peso=60)
        make_seccion(formulario, titulo="B", peso=30)
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 400
        assert "100" in str(r.data) or "peso" in str(r.data).lower()

    def test_publicar_falla_con_pregunta_sin_seccion(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, peso=100)
        make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO)  # sin seccion
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 400
        assert "sección" in str(r.data).lower() or "seccion" in str(r.data).lower() or "huérfana" in str(r.data).lower()

    def test_publicar_exitoso_con_secciones_correctas(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        seccion = make_seccion(formulario, peso=100)
        make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, seccion=seccion)
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 200
        assert r.data["estado"] == "PUBLICADO"

    def test_publicar_exitoso_sin_preguntas_solo_secciones(self, client, admin, periodo):
        """Una sección vacía (sin preguntas) no bloquea publicar."""
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, peso=100)
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# CUADRICULA — tipo Likert (filas × columnas)
# ---------------------------------------------------------------------------


class TestCuadriculaCRUD:
    """PR4: tipo CUADRICULA — filas + columnas (opciones con puntos)."""

    _PAYLOAD_BASE = {
        "tipo": "CUADRICULA",
        "texto": "Evalúa los siguientes aspectos",
        "obligatoria": True,
        "orden": 1,
        "filas": [
            {"texto": "Puntualidad", "orden": 1},
            {"texto": "Participación", "orden": 2},
            {"texto": "Actitud", "orden": 3},
        ],
        "opciones": [
            {"texto": "Nunca", "puntos": 0, "orden": 1},
            {"texto": "A veces", "puntos": 1, "orden": 2},
            {"texto": "Siempre", "puntos": 2, "orden": 3},
        ],
    }

    def test_admin_crea_cuadricula(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        payload = {**self._PAYLOAD_BASE, "formulario": formulario.id}
        r = client.post("/api/v1/preguntas/", payload, format="json")
        assert r.status_code == 201
        assert r.data["tipo"] == "CUADRICULA"
        assert len(r.data["filas"]) == 3
        assert len(r.data["opciones"]) == 3
        assert r.data["filas"][0]["texto"] == "Puntualidad"

    def test_cuadricula_sin_filas_rechazada(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        payload = {**self._PAYLOAD_BASE, "formulario": formulario.id, "filas": []}
        r = client.post("/api/v1/preguntas/", payload, format="json")
        assert r.status_code == 400
        errors = r.data.get("errors", r.data)
        assert "filas" in errors

    def test_cuadricula_sin_opciones_rechazada(self, client, admin, periodo):
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        payload = {**self._PAYLOAD_BASE, "formulario": formulario.id, "opciones": []}
        r = client.post("/api/v1/preguntas/", payload, format="json")
        assert r.status_code == 400
        errors = r.data.get("errors", r.data)
        assert "opciones" in errors

    def test_cuadricula_patch_reemplaza_filas(self, client, admin, periodo):
        """PATCH con nuevas filas reemplaza completamente las existentes."""
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        cr = client.post(
            "/api/v1/preguntas/",
            {**self._PAYLOAD_BASE, "formulario": formulario.id},
            format="json",
        )
        p_id = cr.data["id"]
        r = client.patch(
            f"/api/v1/preguntas/{p_id}/",
            {
                "filas": [
                    {"texto": "Nuevafila 1", "orden": 1},
                    {"texto": "Nuevafila 2", "orden": 2},
                ],
                "opciones": [{"texto": "Sí", "puntos": 1, "orden": 1}],
            },
            format="json",
        )
        assert r.status_code == 200
        assert len(r.data["filas"]) == 2
        assert r.data["filas"][0]["texto"] == "Nuevafila 1"

    def test_cuadricula_filas_en_serializer_publico(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Los profesores ven las filas de CUADRICULA en la vista pública."""
        formulario = make_formulario(periodo, admin)
        seccion = make_seccion(formulario, peso=100)
        auth_admin(client)
        client.post(
            "/api/v1/preguntas/",
            {**self._PAYLOAD_BASE, "formulario": formulario.id, "seccion": seccion.id},
            format="json",
        )
        formulario.publicar()

        auth_prof(client)
        r = client.get("/api/v1/formularios-disponibles/")
        assert r.status_code == 200
        preguntas = r.data["results"][0]["preguntas"]
        cuadricula = next(p for p in preguntas if p["tipo"] == "CUADRICULA")
        assert len(cuadricula["filas"]) == 3
        assert cuadricula["filas"][0]["texto"] == "Puntualidad"


# ---------------------------------------------------------------------------
# CUADRICULA — respuestas del profesor (PR5)
# ---------------------------------------------------------------------------


class TestCuadriculaRespuesta:
    """PR5: responder CUADRICULA con celdas, validación obligatoria por fila, scoring."""

    def _setup(self, periodo, admin):
        """
        Formulario publicado con 1 pregunta CUADRICULA:
          3 filas × 3 columnas (puntos: 0, 1, 2).
          maximo = max(0,1,2) × 3 filas = 6.
        """
        formulario = make_formulario(periodo, admin)
        seccion = make_seccion(formulario, peso=100)
        auth_client = APIClient()
        auth_admin(auth_client)
        r = auth_client.post(
            "/api/v1/preguntas/",
            {
                "formulario": formulario.id,
                "seccion": seccion.id,
                "tipo": "CUADRICULA",
                "texto": "Evalúa cada aspecto",
                "obligatoria": True,
                "orden": 1,
                "filas": [
                    {"texto": "Puntualidad", "orden": 1},
                    {"texto": "Participación", "orden": 2},
                    {"texto": "Actitud", "orden": 3},
                ],
                "opciones": [
                    {"texto": "Nunca", "puntos": 0, "orden": 1},
                    {"texto": "A veces", "puntos": 1, "orden": 2},
                    {"texto": "Siempre", "puntos": 2, "orden": 3},
                ],
            },
            format="json",
        )
        assert r.status_code == 201, r.data
        pregunta_data = r.data
        formulario.publicar()
        return formulario, pregunta_data

    def test_responder_cuadricula_con_celdas(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        formulario, pregunta_data = self._setup(periodo, admin)
        filas = pregunta_data["filas"]
        opciones = pregunta_data["opciones"]
        celdas = [{"fila": f["id"], "opcion": opciones[2]["id"]} for f in filas]

        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [{"pregunta": pregunta_data["id"], "celdas": celdas}],
            },
            format="json",
        )
        assert cr.status_code == 201, cr.data
        r = client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")
        assert r.status_code == 200, r.data
        assert float(r.data["puntaje_obtenido"]) == 6.0
        assert float(r.data["puntaje_maximo"]) == 6.0
        assert float(r.data["porcentaje"]) == 100.0

    def test_puntaje_parcial_cuadricula(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """A veces (1 pt) en 2 filas + Nunca (0 pt) en 1 → obtenido=2, max=6."""
        formulario, pregunta_data = self._setup(periodo, admin)
        filas = pregunta_data["filas"]
        opciones = pregunta_data["opciones"]
        celdas = [
            {"fila": filas[0]["id"], "opcion": opciones[1]["id"]},
            {"fila": filas[1]["id"], "opcion": opciones[1]["id"]},
            {"fila": filas[2]["id"], "opcion": opciones[0]["id"]},
        ]

        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [{"pregunta": pregunta_data["id"], "celdas": celdas}],
            },
            format="json",
        )
        r = client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")
        assert r.status_code == 200
        assert float(r.data["puntaje_obtenido"]) == 2.0
        assert float(r.data["puntaje_maximo"]) == 6.0

    def test_cuadricula_obligatoria_falta_fila(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Obligatoria con fila sin celda → 400 con preguntas_faltantes."""
        formulario, pregunta_data = self._setup(periodo, admin)
        filas = pregunta_data["filas"]
        opciones = pregunta_data["opciones"]
        celdas = [
            {"fila": filas[0]["id"], "opcion": opciones[1]["id"]},
            {"fila": filas[1]["id"], "opcion": opciones[1]["id"]},
            # fila[2] sin responder
        ]

        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [{"pregunta": pregunta_data["id"], "celdas": celdas}],
            },
            format="json",
        )
        r = client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")
        assert r.status_code == 400
        errors = r.data.get("errors", r.data)
        assert "preguntas_faltantes" in errors

    def test_cuadricula_borrador_persiste_celdas(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Guardar borrador con celdas y GET devuelve las celdas guardadas."""
        formulario, pregunta_data = self._setup(periodo, admin)
        filas = pregunta_data["filas"]
        opciones = pregunta_data["opciones"]
        celdas = [{"fila": filas[0]["id"], "opcion": opciones[2]["id"]}]

        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [{"pregunta": pregunta_data["id"], "celdas": celdas}],
            },
            format="json",
        )
        assert cr.status_code == 201
        r = client.get(f"/api/v1/respuestas/{cr.data['id']}/")
        assert r.status_code == 200
        saved_celdas = r.data["items"][0]["celdas"]
        assert len(saved_celdas) == 1
        assert saved_celdas[0]["fila"] == filas[0]["id"]
        assert saved_celdas[0]["opcion"] == opciones[2]["id"]


# ---------------------------------------------------------------------------
# Ponderación por sección — RespuestaSeccion y porcentaje_ponderado (PR6)
# ---------------------------------------------------------------------------


class TestPonderacionPorSeccion:
    """PR6: _calcular_puntaje ponderado, RespuestaSeccion snapshot, secciones_resultado."""

    def _setup_dos_secciones(self, periodo, admin):
        """
        Formulario publicado con 2 secciones:
          - Sec A (peso 70): 1 pregunta OPCION_UNICA, opciones 0/1/2 pts, max=2
          - Sec B (peso 30): 1 pregunta SI_NO (si=1, no=0), max=1

        Calculo esperado si se responde: SecA=max (100%), SecB=si (100%):
          porcentaje_ponderado = 100*70/100 + 100*30/100 = 100%

        Si se responde SecA=0 (0%), SecB=no (0%):
          porcentaje_ponderado = 0

        Si se responde SecA=max (100%), SecB=no (0%):
          porcentaje_ponderado = 100*70/100 + 0*30/100 = 70%
        """
        formulario = make_formulario(periodo, admin)
        sec_a = make_seccion(formulario, titulo="Sección A", peso=70, orden=1)
        sec_b = make_seccion(formulario, titulo="Sección B", peso=30, orden=2)

        p_a = Pregunta.objects.create(
            formulario=formulario, seccion=sec_a,
            tipo=Pregunta.Tipo.OPCION_UNICA, texto="P-A",
            obligatoria=True, orden=1,
        )
        op_a0 = OpcionPregunta.objects.create(pregunta=p_a, texto="Mal", puntos=0, orden=1)
        OpcionPregunta.objects.create(pregunta=p_a, texto="Bien", puntos=1, orden=2)
        op_a_max = OpcionPregunta.objects.create(pregunta=p_a, texto="Excelente", puntos=2, orden=3)

        p_b = Pregunta.objects.create(
            formulario=formulario, seccion=sec_b,
            tipo=Pregunta.Tipo.SI_NO, texto="P-B",
            obligatoria=True, orden=1,
            config={"puntos_si": 1, "puntos_no": 0},
        )

        formulario.publicar()
        return formulario, sec_a, sec_b, p_a, op_a0, op_a_max, p_b

    def test_porcentaje_ponderado_dos_secciones_ambas_maximas(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """SecA 100% (peso 70) + SecB 100% (peso 30) = 100% ponderado."""
        formulario, sec_a, sec_b, p_a, op_a0, op_a_max, p_b = self._setup_dos_secciones(periodo, admin)
        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [
                    {"pregunta": p_a.id, "opciones_seleccionadas": [op_a_max.id]},
                    {"pregunta": p_b.id, "valor_texto": "SI"},
                ],
            },
            format="json",
        )
        r = client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")
        assert r.status_code == 200, r.data
        assert float(r.data["porcentaje"]) == 100.0
        secciones = r.data["secciones_resultado"]
        assert len(secciones) == 2
        sec_a_res = next(s for s in secciones if s["seccion_titulo"] == "Sección A")
        assert float(sec_a_res["peso"]) == 70.0
        assert float(sec_a_res["porcentaje"]) == 100.0
        sec_b_res = next(s for s in secciones if s["seccion_titulo"] == "Sección B")
        assert float(sec_b_res["peso"]) == 30.0
        assert float(sec_b_res["porcentaje"]) == 100.0

    def test_porcentaje_ponderado_seccion_a_llena_b_cero(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """SecA 100% (peso 70) + SecB 0% (peso 30) = 70% ponderado."""
        formulario, sec_a, sec_b, p_a, op_a0, op_a_max, p_b = self._setup_dos_secciones(periodo, admin)
        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [
                    {"pregunta": p_a.id, "opciones_seleccionadas": [op_a_max.id]},
                    {"pregunta": p_b.id, "valor_texto": "NO"},
                ],
            },
            format="json",
        )
        r = client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")
        assert r.status_code == 200, r.data
        assert float(r.data["porcentaje"]) == 70.0
        secciones = r.data["secciones_resultado"]
        sec_a_res = next(s for s in secciones if s["seccion_titulo"] == "Sección A")
        assert float(sec_a_res["porcentaje"]) == 100.0
        sec_b_res = next(s for s in secciones if s["seccion_titulo"] == "Sección B")
        assert float(sec_b_res["porcentaje"]) == 0.0

    def test_respuesta_seccion_snapshot_peso(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """RespuestaSeccion guarda snapshot del peso en la BD."""
        formulario, sec_a, sec_b, p_a, op_a0, op_a_max, p_b = self._setup_dos_secciones(periodo, admin)
        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [
                    {"pregunta": p_a.id, "opciones_seleccionadas": [op_a_max.id]},
                    {"pregunta": p_b.id, "valor_texto": "SI"},
                ],
            },
            format="json",
        )
        client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")

        resp_a = RespuestaSeccion.objects.get(respuesta_id=cr.data["id"], seccion=sec_a)
        resp_b = RespuestaSeccion.objects.get(respuesta_id=cr.data["id"], seccion=sec_b)
        assert float(resp_a.peso) == 70.0
        assert float(resp_b.peso) == 30.0

    def test_seccion_sin_respuesta_da_cero(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Si el profesor no responde preguntas de una sección, porcentaje_seccion = 0."""
        formulario = make_formulario(periodo, admin)
        sec_a = make_seccion(formulario, titulo="Sección A", peso=70, orden=1)
        sec_b = make_seccion(formulario, titulo="Sección B", peso=30, orden=2)

        # Solo preguntas en sec_a; sec_b tiene preguntas de texto (no puntables)
        p_a = Pregunta.objects.create(
            formulario=formulario, seccion=sec_a,
            tipo=Pregunta.Tipo.OPCION_UNICA, texto="P-A",
            obligatoria=True, orden=1,
        )
        op_max = OpcionPregunta.objects.create(pregunta=p_a, texto="Max", puntos=2, orden=1)

        p_b_texto = Pregunta.objects.create(
            formulario=formulario, seccion=sec_b,
            tipo=Pregunta.Tipo.TEXTO_CORTO, texto="P-B texto",
            obligatoria=True, orden=1,
        )

        formulario.publicar()
        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [
                    {"pregunta": p_a.id, "opciones_seleccionadas": [op_max.id]},
                    {"pregunta": p_b_texto.id, "valor_texto": "Texto libre"},
                ],
            },
            format="json",
        )
        r = client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")
        assert r.status_code == 200, r.data
        # SecA: 100% × 70/100 = 70; SecB: 0 puntable → 0% × 30/100 = 0 → total = 70
        assert float(r.data["porcentaje"]) == 70.0
        secciones = r.data["secciones_resultado"]
        sec_b_res = next(s for s in secciones if s["seccion_titulo"] == "Sección B")
        assert float(sec_b_res["puntaje_maximo"]) == 0.0
        assert float(sec_b_res["porcentaje"]) == 0.0


# ---------------------------------------------------------------------------
# Estadísticas por sección — endpoint /estadisticas/ (PR7)
# ---------------------------------------------------------------------------


class TestEstadisticasPorSeccion:
    """PR7: por_seccion en payload de estadísticas."""

    def _setup(self, periodo, admin):
        """
        Formulario con 2 secciones (peso 60/40) y una pregunta OPCION_UNICA por sección.
          Sec A (peso 60): opciones 0/2 pts
          Sec B (peso 40): opciones 0/4 pts
        """
        formulario = make_formulario(periodo, admin)
        sec_a = make_seccion(formulario, titulo="Sec A", peso=60, orden=1)
        sec_b = make_seccion(formulario, titulo="Sec B", peso=40, orden=2)

        p_a = Pregunta.objects.create(
            formulario=formulario, seccion=sec_a,
            tipo=Pregunta.Tipo.OPCION_UNICA, texto="P-A",
            obligatoria=True, orden=1,
        )
        op_a0 = OpcionPregunta.objects.create(pregunta=p_a, texto="Mal", puntos=0, orden=1)
        op_a_max = OpcionPregunta.objects.create(pregunta=p_a, texto="Max", puntos=2, orden=2)

        p_b = Pregunta.objects.create(
            formulario=formulario, seccion=sec_b,
            tipo=Pregunta.Tipo.OPCION_UNICA, texto="P-B",
            obligatoria=True, orden=1,
        )
        op_b0 = OpcionPregunta.objects.create(pregunta=p_b, texto="Mal", puntos=0, orden=1)
        op_b_max = OpcionPregunta.objects.create(pregunta=p_b, texto="Max", puntos=4, orden=2)

        formulario.publicar()
        return formulario, sec_a, sec_b, p_a, op_a0, op_a_max, p_b, op_b0, op_b_max

    def test_por_seccion_en_payload(self, client, admin, periodo):
        """El endpoint siempre incluye la clave por_seccion."""
        auth_admin(client)
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, titulo="General", peso=100)
        r = client.get(f"/api/v1/formularios/{formulario.id}/estadisticas/")
        assert r.status_code == 200
        assert "por_seccion" in r.data
        assert isinstance(r.data["por_seccion"], list)
        assert len(r.data["por_seccion"]) == 1
        assert r.data["por_seccion"][0]["titulo"] == "General"
        assert r.data["por_seccion"][0]["promedio_porcentaje"] is None  # sin respuestas

    def test_promedio_por_seccion_un_profesor(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Con una respuesta enviada, el promedio coincide con el porcentaje obtenido."""
        (formulario, sec_a, sec_b,
         p_a, op_a0, op_a_max, p_b, op_b0, op_b_max) = self._setup(periodo, admin)

        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [
                    {"pregunta": p_a.id, "opciones_seleccionadas": [op_a_max.id]},  # 100%
                    {"pregunta": p_b.id, "opciones_seleccionadas": [op_b0.id]},     # 0%
                ],
            },
            format="json",
        )
        client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")

        auth_admin(client)
        r = client.get(f"/api/v1/formularios/{formulario.id}/estadisticas/")
        assert r.status_code == 200
        por_seccion = r.data["por_seccion"]
        sec_a_stat = next(s for s in por_seccion if s["titulo"] == "Sec A")
        sec_b_stat = next(s for s in por_seccion if s["titulo"] == "Sec B")
        assert sec_a_stat["promedio_porcentaje"] == 100.0
        assert sec_b_stat["promedio_porcentaje"] == 0.0
        assert sec_a_stat["total_con_datos"] == 1
        assert sec_b_stat["total_con_datos"] == 1

    def test_promedio_por_seccion_varios_profesores(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Promedio de SecA: (100 + 0) / 2 = 50."""
        (formulario, sec_a, sec_b,
         p_a, op_a0, op_a_max, p_b, op_b0, op_b_max) = self._setup(periodo, admin)
        from accounts.models import Usuario as U

        for i, (a_op, b_op) in enumerate([(op_a_max, op_b_max), (op_a0, op_b0)]):
            u = U.objects.create_user(
                email=f"pstat7_{i}@uam.mx", nombre=f"P7-{i}", password="P1234!",
                rol=U.Rol.PROFESOR,
            )
            p = Profesor.objects.create(
                usuario=u, nombre_completo=f"P7-{i}",
                correo_institucional=f"pstat7_{i}@inst.mx",
                departamento=profesor.departamento,
            )
            c = APIClient()
            r_login = c.post(
                "/api/v1/auth/login/",
                {"email": f"pstat7_{i}@uam.mx", "password": "P1234!"},
                format="json",
            )
            c.credentials(HTTP_AUTHORIZATION=f"Bearer {r_login.data['access']}")
            cr = c.post(
                "/api/v1/respuestas/",
                {
                    "formulario": formulario.id,
                    "items": [
                        {"pregunta": p_a.id, "opciones_seleccionadas": [a_op.id]},
                        {"pregunta": p_b.id, "opciones_seleccionadas": [b_op.id]},
                    ],
                },
                format="json",
            )
            c.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")

        auth_admin(client)
        r = client.get(f"/api/v1/formularios/{formulario.id}/estadisticas/")
        por_seccion = r.data["por_seccion"]
        sec_a_stat = next(s for s in por_seccion if s["titulo"] == "Sec A")
        # Prof 1: SecA 100%, Prof 2: SecA 0% → promedio 50%
        assert sec_a_stat["promedio_porcentaje"] == 50.0
        assert sec_a_stat["total_con_datos"] == 2

    def test_estadisticas_por_seccion_filtra_version(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """por_seccion respeta el filtro de version — respuestas de v1 no aparecen en v2."""
        (formulario, sec_a, sec_b,
         p_a, op_a0, op_a_max, p_b, op_b0, op_b_max) = self._setup(periodo, admin)

        # Responde v1
        auth_prof(client)
        cr = client.post(
            "/api/v1/respuestas/",
            {
                "formulario": formulario.id,
                "items": [
                    {"pregunta": p_a.id, "opciones_seleccionadas": [op_a_max.id]},
                    {"pregunta": p_b.id, "opciones_seleccionadas": [op_b_max.id]},
                ],
            },
            format="json",
        )
        client.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")

        # Admin publica v2
        auth_admin(client)
        client.post(f"/api/v1/formularios/{formulario.id}/cerrar/")
        client.post(f"/api/v1/formularios/{formulario.id}/publicar-revision/")

        # Sin ?version → v2 → sin datos
        r = client.get(f"/api/v1/formularios/{formulario.id}/estadisticas/")
        assert r.data["version"] == 2
        sec_a_v2 = next(s for s in r.data["por_seccion"] if s["titulo"] == "Sec A")
        assert sec_a_v2["promedio_porcentaje"] is None

        # Con ?version=1 → ve los datos de v1
        r2 = client.get(f"/api/v1/formularios/{formulario.id}/estadisticas/?version=1")
        sec_a_v1 = next(s for s in r2.data["por_seccion"] if s["titulo"] == "Sec A")
        assert sec_a_v1["promedio_porcentaje"] == 100.0


# ---------------------------------------------------------------------------
# Edición de CUADRICULA con respuestas previas (PR8-A)
# ---------------------------------------------------------------------------


class TestEdicionConRespuestasPrevias:
    """Modificar opciones/filas de CUADRICULA cuando ya existen RespuestaCelda."""

    def _setup(self, periodo, admin, usuario_prof, profesor):
        """
        Crea formulario BORRADOR con CUADRICULA (3 filas × 3 opciones),
        lo publica, el profesor envía respuesta con 'Alto' en todas las filas,
        luego lo despublica → queda en BORRADOR editable.

        Retorna (formulario, pregunta_data) donde pregunta_data tiene .id,
        .filas y .opciones con sus IDs.
        """
        formulario = make_formulario(periodo, admin)
        seccion = make_seccion(formulario, peso=100)
        ac = APIClient()
        auth_admin(ac)
        pr = ac.post(
            "/api/v1/preguntas/",
            {
                "formulario": formulario.id,
                "seccion": seccion.id,
                "tipo": "CUADRICULA",
                "texto": "Evalúa cada aspecto",
                "obligatoria": True,
                "orden": 1,
                "filas": [
                    {"texto": "Puntualidad", "orden": 1},
                    {"texto": "Dominio", "orden": 2},
                    {"texto": "Claridad", "orden": 3},
                ],
                "opciones": [
                    {"texto": "Bajo", "puntos": 0, "orden": 1},
                    {"texto": "Medio", "puntos": 1, "orden": 2},
                    {"texto": "Alto", "puntos": 2, "orden": 3},
                ],
            },
            format="json",
        )
        assert pr.status_code == 201, pr.data
        pregunta_data = pr.data

        # Publica
        formulario.publicar()

        # Profesor responde con 'Alto' en todas las filas
        pc = APIClient()
        auth_prof(pc)
        filas = pregunta_data["filas"]
        alto_id = pregunta_data["opciones"][2]["id"]
        celdas = [{"fila": f["id"], "opcion": alto_id} for f in filas]
        cr = pc.post(
            "/api/v1/respuestas/",
            {"formulario": formulario.id, "items": [{"pregunta": pregunta_data["id"], "celdas": celdas}]},
            format="json",
        )
        assert cr.status_code == 201, cr.data
        er = pc.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")
        assert er.status_code == 200, er.data

        # Admin despublica → BORRADOR
        formulario.despublicar()

        return formulario, pregunta_data

    def test_modificar_opcion_cuadricula_con_respuestas_no_500(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """PATCH con id en opciones/filas existentes → 200, sin ProtectedError."""
        formulario, pd = self._setup(periodo, admin, usuario_prof, profesor)
        auth_admin(client)
        opciones_payload = [
            {"id": op["id"], "texto": op["texto"], "valor": "", "puntos": float(op["puntos"]) + 1, "orden": op["orden"]}
            for op in pd["opciones"]
        ]
        filas_payload = [
            {"id": f["id"], "texto": f["texto"], "orden": f["orden"]}
            for f in pd["filas"]
        ]
        r = client.patch(
            f"/api/v1/preguntas/{pd['id']}/",
            {"tipo": "CUADRICULA", "texto": pd["texto"], "opciones": opciones_payload, "filas": filas_payload},
            format="json",
        )
        assert r.status_code == 200, r.data
        # Los puntos se actualizaron
        puntos_actualizados = [float(op["puntos"]) for op in r.data["opciones"]]
        assert puntos_actualizados == [1.0, 2.0, 3.0]

    def test_agregar_opcion_cuadricula_con_respuestas(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Añadir una nueva opción (sin id) al payload → 200; count = 4."""
        formulario, pd = self._setup(periodo, admin, usuario_prof, profesor)
        auth_admin(client)
        opciones_payload = [
            {"id": op["id"], "texto": op["texto"], "valor": "", "puntos": op["puntos"], "orden": op["orden"]}
            for op in pd["opciones"]
        ] + [{"texto": "Muy Alto", "valor": "", "puntos": 3, "orden": 4}]
        filas_payload = [
            {"id": f["id"], "texto": f["texto"], "orden": f["orden"]}
            for f in pd["filas"]
        ]
        r = client.patch(
            f"/api/v1/preguntas/{pd['id']}/",
            {"tipo": "CUADRICULA", "texto": pd["texto"], "opciones": opciones_payload, "filas": filas_payload},
            format="json",
        )
        assert r.status_code == 200, r.data
        assert len(r.data["opciones"]) == 4

    def test_quitar_opcion_referenciada_se_preserva(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """
        Opción 'Alto' (referenciada por RespuestaCelda) omitida del payload → preservada.
        Opción 'Medio' (no referenciada) omitida → eliminada.
        """
        formulario, pd = self._setup(periodo, admin, usuario_prof, profesor)
        auth_admin(client)
        bajo_id = pd["opciones"][0]["id"]
        alto_id = pd["opciones"][2]["id"]

        # Solo mandamos 'Bajo' (con id); omitimos 'Medio' y 'Alto'
        opciones_payload = [
            {"id": bajo_id, "texto": "Bajo", "valor": "", "puntos": 0, "orden": 1}
        ]
        filas_payload = [
            {"id": f["id"], "texto": f["texto"], "orden": f["orden"]}
            for f in pd["filas"]
        ]
        r = client.patch(
            f"/api/v1/preguntas/{pd['id']}/",
            {"tipo": "CUADRICULA", "texto": pd["texto"], "opciones": opciones_payload, "filas": filas_payload},
            format="json",
        )
        assert r.status_code == 200, r.data
        opciones_ids = {op["id"] for op in r.data["opciones"]}
        # 'Alto' se preservó (referenciada), 'Medio' se borró
        assert alto_id in opciones_ids
        assert bajo_id in opciones_ids
        assert len(opciones_ids) == 2

    def test_modificar_fila_cuadricula_con_respuestas(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """PATCH cambiando texto de fila existente (con id) → 200, sin ProtectedError."""
        formulario, pd = self._setup(periodo, admin, usuario_prof, profesor)
        auth_admin(client)
        filas_payload = [
            {"id": f["id"], "texto": f"Fila modificada {f['orden']}", "orden": f["orden"]}
            for f in pd["filas"]
        ]
        opciones_payload = [
            {"id": op["id"], "texto": op["texto"], "valor": "", "puntos": op["puntos"], "orden": op["orden"]}
            for op in pd["opciones"]
        ]
        r = client.patch(
            f"/api/v1/preguntas/{pd['id']}/",
            {"tipo": "CUADRICULA", "texto": pd["texto"], "filas": filas_payload, "opciones": opciones_payload},
            format="json",
        )
        assert r.status_code == 200, r.data
        assert r.data["filas"][0]["texto"] == "Fila modificada 1"


# ---------------------------------------------------------------------------
# Versionado al republicar con respuestas previas (PR8-B)
# ---------------------------------------------------------------------------


class TestVersionadoAlPublicarConRespuestas:
    """publicar() incrementa versión si ya hay respuestas en esa versión."""

    def _make_formulario_con_respuesta(self, periodo, admin, profesor, usuario_prof):
        """Formulario v1 publicado con 1 respuesta enviada. Devuelve formulario."""
        formulario = make_formulario(periodo, admin)
        seccion = make_seccion(formulario, peso=100)
        pregunta = make_pregunta(formulario, tipo=Pregunta.Tipo.TEXTO_CORTO, seccion=seccion)
        formulario.publicar()

        pc = APIClient()
        auth_prof(pc)
        cr = pc.post(
            "/api/v1/respuestas/",
            {"formulario": formulario.id, "items": [{"pregunta": pregunta.id, "valor_texto": "ok"}]},
            format="json",
        )
        pc.post(f"/api/v1/respuestas/{cr.data['id']}/enviar/")

        formulario.despublicar()
        formulario.refresh_from_db()
        return formulario

    def test_publicar_incrementa_version_si_hay_respuestas_previas(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        formulario = self._make_formulario_con_respuesta(periodo, admin, profesor, usuario_prof)
        assert formulario.version == 1
        auth_admin(client)
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 200, r.data
        assert r.data["version"] == 2
        formulario.refresh_from_db()
        assert formulario.version == 2

    def test_publicar_no_incrementa_sin_respuestas(
        self, client, admin, periodo
    ):
        formulario = make_formulario(periodo, admin)
        make_seccion(formulario, peso=100)
        auth_admin(client)
        # Primera publicación sin respuestas
        r = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r.status_code == 200
        assert r.data["version"] == 1
        # Despublica y republica sin que nadie haya respondido
        formulario.refresh_from_db()
        formulario.despublicar()
        r2 = client.post(f"/api/v1/formularios/{formulario.id}/publicar/")
        assert r2.status_code == 200
        assert r2.data["version"] == 1

    def test_profesor_ve_pendiente_tras_republicar_editado(
        self, client, admin, usuario_prof, profesor, periodo
    ):
        """Tras el incremento de versión, el profesor ve ya_respondido=false."""
        formulario = self._make_formulario_con_respuesta(periodo, admin, profesor, usuario_prof)
        # Admin republica → sube a v2
        auth_admin(client)
        client.post(f"/api/v1/formularios/{formulario.id}/publicar/")

        # Profesor consulta formularios disponibles
        auth_prof(client)
        r = client.get("/api/v1/formularios-disponibles/")
        assert r.status_code == 200
        resultados = r.data["results"]
        form_data = next((f for f in resultados if f["id"] == formulario.id), None)
        assert form_data is not None
        assert form_data["version"] == 2
        assert form_data["ya_respondido"] is False
        assert form_data["respuesta_id"] is None
