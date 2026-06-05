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
