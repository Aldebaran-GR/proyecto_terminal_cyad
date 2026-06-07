"""Tests de autenticación JWT y permisos por rol — M1."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Usuario


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return Usuario.objects.create_user(
        email="admin_test@cyad.uam.mx",
        nombre="Admin Test",
        password="Admin1234!",
        rol=Usuario.Rol.ADMIN,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def profesor_user(db):
    return Usuario.objects.create_user(
        email="profesor_test@cyad.uam.mx",
        nombre="Profesor Test",
        password="Profesor1234!",
        rol=Usuario.Rol.PROFESOR,
    )


def get_token(client, email, password):
    """Helper: obtiene el access token para un usuario."""
    res = client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
    )
    return res.data.get("access")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
class TestLogin:
    def test_login_exitoso_admin(self, client, admin_user):
        res = client.post(
            "/api/v1/auth/login/",
            {"email": "admin_test@cyad.uam.mx", "password": "Admin1234!"},
            format="json",
        )
        assert res.status_code == 200
        assert "access" in res.data
        assert "refresh" in res.data
        assert res.data["user"]["rol"] == "ADMIN"

    def test_login_exitoso_profesor(self, client, profesor_user):
        res = client.post(
            "/api/v1/auth/login/",
            {"email": "profesor_test@cyad.uam.mx", "password": "Profesor1234!"},
            format="json",
        )
        assert res.status_code == 200
        assert res.data["user"]["rol"] == "PROFESOR"

    def test_login_credenciales_invalidas(self, client, admin_user):
        res = client.post(
            "/api/v1/auth/login/",
            {"email": "admin_test@cyad.uam.mx", "password": "wrongpass"},
            format="json",
        )
        assert res.status_code == 401

    def test_login_usuario_inactivo(self, client, db):
        u = Usuario.objects.create_user(
            email="inactivo@cyad.uam.mx",
            nombre="Inactivo",
            password="Test1234!",
            is_active=False,
        )
        res = client.post(
            "/api/v1/auth/login/",
            {"email": u.email, "password": "Test1234!"},
            format="json",
        )
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# /me/
# ---------------------------------------------------------------------------
class TestMe:
    def test_me_autenticado(self, client, admin_user):
        token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = client.get("/api/v1/auth/me/")
        assert res.status_code == 200
        assert res.data["data"]["rol"] == "ADMIN"

    def test_me_sin_token(self, client):
        res = client.get("/api/v1/auth/me/")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Permisos por rol
# ---------------------------------------------------------------------------
class TestPermisosPorRol:
    def test_profesor_no_accede_a_usuarios(self, client, profesor_user):
        token = get_token(client, "profesor_test@cyad.uam.mx", "Profesor1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = client.get("/api/v1/usuarios/")
        assert res.status_code == 403

    def test_admin_accede_a_usuarios(self, client, admin_user):
        token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = client.get("/api/v1/usuarios/")
        assert res.status_code == 200

    def test_sin_token_bloqueado(self, client):
        res = client.get("/api/v1/usuarios/")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Restablecer contraseña (admin)
# ---------------------------------------------------------------------------
class TestSetPassword:
    def test_admin_restablece_contrasena(self, client, admin_user, profesor_user):
        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        r = client.post(
            f"/api/v1/usuarios/{profesor_user.id}/set-password/",
            {"password": "NuevoPwd9876!"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["success"] is True
        # El profesor puede iniciar sesión con la nueva contraseña
        client.credentials()
        login = client.post(
            "/api/v1/auth/login/",
            {"email": "profesor_test@cyad.uam.mx", "password": "NuevoPwd9876!"},
            format="json",
        )
        assert login.status_code == 200

    def test_profesor_no_restablece_contrasena(self, client, profesor_user):
        """Un profesor no puede llamar al endpoint (solo ADMIN)."""
        prof_token = get_token(client, "profesor_test@cyad.uam.mx", "Profesor1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {prof_token}")
        r = client.post(
            f"/api/v1/usuarios/{profesor_user.id}/set-password/",
            {"password": "Cualquiera1!"},
            format="json",
        )
        assert r.status_code == 403

    def test_crear_usuario_devuelve_id(self, client, admin_user, db):
        """POST /usuarios/ debe regresar el id para encadenar /profesores/."""
        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        r = client.post(
            "/api/v1/usuarios/",
            {
                "email": "nuevo_prof@uam.mx",
                "nombre": "Nuevo Profesor",
                "password": "Profesor1234!",
                "rol": "PROFESOR",
            },
            format="json",
        )
        assert r.status_code == 201, r.data
        assert "id" in r.data
        assert isinstance(r.data["id"], int)

    def test_crear_profesor_acepta_departamento(self, client, admin_user, db):
        """POST /profesores/ acepta el FK `departamento`."""
        from accounts.models import Usuario
        from catalogos.models import Departamento
        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        # Pre-requisitos
        user = Usuario.objects.create_user(
            email="prof_depto@uam.mx", nombre="X", password="Profesor1234!",
            rol=Usuario.Rol.PROFESOR,
        )
        depto = Departamento.objects.create(clave="DPT-X", nombre="Depto X")
        r = client.post(
            "/api/v1/profesores/",
            {
                "usuario_id": user.id,
                "nombre_completo": "X Y Z",
                "correo_institucional": "prof_depto@uam.mx",
                "departamento": depto.id,
            },
            format="json",
        )
        assert r.status_code == 201, r.data
        assert r.data["departamento"] == depto.id
        assert r.data["departamento_nombre"] == "Depto X"

    def test_crear_con_usuario_atomico(self, client, admin_user, db):
        """Crea Usuario + Profesor en una sola llamada atómica."""
        from accounts.models import Profesor, Usuario
        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        r = client.post(
            "/api/v1/profesores/crear-con-usuario/",
            {
                "email": "atomico@uam.mx",
                "password": "Profesor1234!",
                "nombre_completo": "Atómico Test",
            },
            format="json",
        )
        assert r.status_code == 201, r.data
        # Usuario y Profesor existen y están enlazados
        u = Usuario.objects.get(email="atomico@uam.mx")
        assert Profesor.objects.filter(usuario=u).exists()
        assert u.rol == "PROFESOR"

    def test_crear_con_usuario_reutiliza_huerfano(self, client, admin_user, db):
        """Si existe un Usuario con ese email pero SIN perfil de profesor
        (huérfano), se reutiliza con la nueva contraseña."""
        from accounts.models import Profesor, Usuario
        Usuario.objects.create_user(
            email="huerfano@uam.mx", nombre="Huérfano", password="oldPwd1234!",
            rol=Usuario.Rol.PROFESOR,
        )
        assert not Profesor.objects.filter(usuario__email="huerfano@uam.mx").exists()

        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        r = client.post(
            "/api/v1/profesores/crear-con-usuario/",
            {
                "email": "huerfano@uam.mx",
                "password": "NuevaPwd1234!",
                "nombre_completo": "Recuperado",
            },
            format="json",
        )
        assert r.status_code == 201, r.data
        # No se crea otro Usuario duplicado: solo hay uno con ese email
        assert Usuario.objects.filter(email="huerfano@uam.mx").count() == 1
        # Y ahora tiene perfil de profesor
        assert Profesor.objects.filter(usuario__email="huerfano@uam.mx").exists()
        # Y la nueva contraseña funciona
        client.credentials()
        login = client.post(
            "/api/v1/auth/login/",
            {"email": "huerfano@uam.mx", "password": "NuevaPwd1234!"},
            format="json",
        )
        assert login.status_code == 200

    def test_crear_con_usuario_rechaza_email_ya_profesor(self, client, admin_user, profesor_user):
        """Si el email ya tiene perfil de profesor, regresa 400 explicando."""
        from accounts.models import Profesor
        Profesor.objects.create(
            usuario=profesor_user,
            nombre_completo="Existente",
            correo_institucional="profesor_test@cyad.uam.mx",
        )
        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        r = client.post(
            "/api/v1/profesores/crear-con-usuario/",
            {
                "email": "profesor_test@cyad.uam.mx",
                "password": "OtraPwd1234!",
                "nombre_completo": "Quiere duplicar",
            },
            format="json",
        )
        assert r.status_code == 400
        errors = r.data.get("errors") or r.data
        assert "email" in errors

    def test_crear_con_usuario_rollback_si_falla_profesor(self, client, admin_user, db):
        """Si la creación del Profesor falla por integridad, el Usuario
        recién creado se debe haber rollback (no queda huérfano)."""
        from accounts.models import Profesor, Usuario
        # Pre-crear un Profesor con un numero_economico para forzar conflicto
        u_existente = Usuario.objects.create_user(
            email="existente@uam.mx", nombre="X", password="Profesor1234!",
            rol=Usuario.Rol.PROFESOR,
        )
        Profesor.objects.create(
            usuario=u_existente, nombre_completo="X",
            correo_institucional="existente@uam.mx", numero_economico="ECO1",
        )
        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        # Intento crear otro profesor reutilizando numero_economico="ECO1"
        # (unique=True a nivel BD → falla al insertar el Profesor).
        r = client.post(
            "/api/v1/profesores/crear-con-usuario/",
            {
                "email": "nuevo_huerfano_no@uam.mx",
                "password": "Profesor1234!",
                "nombre_completo": "Falla",
                "numero_economico": "ECO1",
            },
            format="json",
        )
        assert r.status_code == 400
        # Y el Usuario no debe haberse quedado huérfano
        assert not Usuario.objects.filter(email="nuevo_huerfano_no@uam.mx").exists()

    def test_eliminar_profesor_conserva_documentos(self, client, admin_user, db):
        """Eliminar el profesor borra el Usuario pero conserva sus
        documentos con el snapshot del nombre/correo."""
        from accounts.models import Profesor, Usuario
        from catalogos.models import Departamento, Licenciatura, Periodo, UEA
        from documentos.models import CartaTematica

        depto = Departamento.objects.create(clave="DEL", nombre="Depto Del")
        lic = Licenciatura.objects.create(clave="DEL-L", nombre="Lic Del", departamento=depto)
        uea = UEA.objects.create(clave="DEL-UEA", nombre="UEA Del", licenciatura=lic)
        periodo = Periodo.objects.create(
            clave="DEL-PER", fecha_inicio="2026-01-01", fecha_fin="2026-04-30",
            activo_cartas=True,
        )
        # Crear usuario + profesor
        u = Usuario.objects.create_user(
            email="aborrar@uam.mx", nombre="A Borrar",
            password="Profesor1234!", rol=Usuario.Rol.PROFESOR,
        )
        prof = Profesor.objects.create(
            usuario=u, nombre_completo="A Borrar Snapshot",
            correo_institucional="aborrar@uam.mx", departamento=depto,
        )
        # Crear una carta a su nombre con snapshot
        carta = CartaTematica.objects.create(
            profesor=prof, uea=uea, periodo=periodo,
            nombre_grupo="HIST", id_grupo="HIST-1", horario="L 10-12",
            profesor_nombre=prof.nombre_completo,
            profesor_correo=prof.correo_institucional,
        )

        # El admin borra el profesor
        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        r = client.delete(f"/api/v1/profesores/{prof.id}/")
        assert r.status_code == 204, r.data

        # El Usuario y el Profesor se fueron
        assert not Usuario.objects.filter(pk=u.id).exists()
        assert not Profesor.objects.filter(pk=prof.id).exists()
        # La Carta sigue existiendo, con profesor=NULL y snapshot intacto
        carta.refresh_from_db()
        assert carta.profesor_id is None
        assert carta.profesor_nombre == "A Borrar Snapshot"
        assert carta.profesor_correo == "aborrar@uam.mx"

    def test_desactivar_profesor_bloquea_login(self, client, admin_user, db):
        """Al desactivar el perfil del profesor (estado=False), su Usuario
        queda inactivo y no puede iniciar sesión."""
        from accounts.models import Profesor, Usuario
        u = Usuario.objects.create_user(
            email="inactivar@uam.mx", nombre="X",
            password="Profesor1234!", rol=Usuario.Rol.PROFESOR,
        )
        prof = Profesor.objects.create(
            usuario=u, nombre_completo="X",
            correo_institucional="inactivar@uam.mx",
        )
        # Antes de desactivar, login funciona
        login = client.post(
            "/api/v1/auth/login/",
            {"email": "inactivar@uam.mx", "password": "Profesor1234!"},
            format="json",
        )
        assert login.status_code == 200

        # Admin desactiva el perfil
        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        r = client.patch(
            f"/api/v1/profesores/{prof.id}/",
            {"estado": False},
            format="json",
        )
        assert r.status_code == 200, r.data

        # El Usuario quedó inactivo automáticamente
        u.refresh_from_db()
        assert u.is_active is False

        # Login ya no funciona — y devuelve el código específico
        # `account_disabled` para que el frontend muestre el mensaje
        # "contacta al administrador" en vez del genérico de credenciales.
        client.credentials()
        login_blocked = client.post(
            "/api/v1/auth/login/",
            {"email": "inactivar@uam.mx", "password": "Profesor1234!"},
            format="json",
        )
        assert login_blocked.status_code == 401
        # El api_exception_handler envuelve la respuesta:
        # { success, status_code, errors: { code, detail } }
        payload = login_blocked.data.get("errors") or login_blocked.data
        assert payload.get("code") == "account_disabled", payload
        assert "administrador" in (payload.get("detail") or "").lower()

    def test_login_credenciales_incorrectas_no_es_account_disabled(
        self, client, profesor_user, db,
    ):
        """Con cuenta activa pero contraseña incorrecta, el 401 NO trae el
        código `account_disabled` — para que el frontend muestre el mensaje
        genérico de credenciales en vez del de cuenta desactivada."""
        client.credentials()
        r = client.post(
            "/api/v1/auth/login/",
            {"email": profesor_user.email, "password": "ContrasenaIncorrecta!"},
            format="json",
        )
        assert r.status_code == 401
        payload = r.data.get("errors") or r.data
        # SimpleJWT estándar devuelve { detail: "..." } sin campo code.
        assert payload.get("code") != "account_disabled", payload

    def test_reactivar_profesor_restaura_login(self, client, admin_user, db):
        """Volver a marcar estado=True reactiva el Usuario."""
        from accounts.models import Profesor, Usuario
        u = Usuario.objects.create_user(
            email="reactivar@uam.mx", nombre="X",
            password="Profesor1234!", rol=Usuario.Rol.PROFESOR,
            is_active=False,
        )
        prof = Profesor.objects.create(
            usuario=u, nombre_completo="X",
            correo_institucional="reactivar@uam.mx",
            estado=False,
        )
        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        r = client.patch(
            f"/api/v1/profesores/{prof.id}/", {"estado": True}, format="json",
        )
        assert r.status_code == 200
        u.refresh_from_db()
        assert u.is_active is True

    def test_password_invalida_rechazada(self, client, admin_user, profesor_user):
        admin_token = get_token(client, "admin_test@cyad.uam.mx", "Admin1234!")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        r = client.post(
            f"/api/v1/usuarios/{profesor_user.id}/set-password/",
            {"password": "abc"},  # demasiado corta
            format="json",
        )
        assert r.status_code == 400
        # El wrapper de errores de DRF usa data.errors.password
        errors_dict = r.data.get("errors") or r.data
        assert "password" in errors_dict


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------
class TestRefreshToken:
    def test_refresh_valido(self, client, admin_user):
        login = client.post(
            "/api/v1/auth/login/",
            {"email": "admin_test@cyad.uam.mx", "password": "Admin1234!"},
            format="json",
        )
        res = client.post(
            "/api/v1/auth/refresh/",
            {"refresh": login.data["refresh"]},
            format="json",
        )
        assert res.status_code == 200
        assert "access" in res.data

    def test_refresh_invalido(self, client):
        res = client.post(
            "/api/v1/auth/refresh/",
            {"refresh": "token.invalido.aqui"},
            format="json",
        )
        assert res.status_code == 401
