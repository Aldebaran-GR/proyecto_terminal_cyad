"""Permisos por rol y a nivel de objeto."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdmin(BasePermission):
    """Permite el acceso únicamente a usuarios con rol ADMIN."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.es_admin
        )


class IsProfesor(BasePermission):
    """Permite el acceso únicamente a usuarios con rol PROFESOR."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.es_profesor
        )


class IsAdminOrReadOnly(BasePermission):
    """Lectura para cualquier autenticado; escritura solo para ADMIN."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.es_admin


class IsOwnerProfesorOrAdminReadOnly(BasePermission):
    """El profesor dueño puede leer/escribir; el admin solo puede leer.

    - has_permission: bloquea escrituras del admin a nivel de vista.
    - has_object_permission: bloquea que un profesor edite objetos ajenos.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        # Admin solo puede leer
        if user.es_admin:
            return request.method in SAFE_METHODS
        # Solo profesores con perfil pueden escribir
        return user.es_profesor

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.es_admin:
            return request.method in SAFE_METHODS
        profesor = getattr(obj, "profesor", None)
        return bool(profesor and profesor.usuario_id == user.id)
