"""Modelos de autenticación y perfil de profesor."""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from core.models import EstadoActivoModel, TimeStampedModel

from .managers import UsuarioManager

# FK a catalogos.Departamento referida como string para evitar importación circular.
_DEPARTAMENTO = "catalogos.Departamento"


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Usuario del sistema. El email es el identificador de acceso."""

    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        PROFESOR = "PROFESOR", "Profesor"

    email = models.EmailField("Correo", unique=True)
    nombre = models.CharField("Nombre", max_length=255)
    rol = models.CharField(
        "Rol", max_length=10, choices=Rol.choices, default=Rol.PROFESOR
    )

    is_active = models.BooleanField("Activo", default=True)
    is_staff = models.BooleanField("Acceso al admin", default=False)

    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.email})"

    @property
    def es_admin(self):
        return self.rol == self.Rol.ADMIN

    @property
    def es_profesor(self):
        return self.rol == self.Rol.PROFESOR


class Profesor(TimeStampedModel, EstadoActivoModel):
    """Perfil extendido del usuario con rol PROFESOR."""

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name="perfil_profesor",
        limit_choices_to={"rol": Usuario.Rol.PROFESOR},
    )
    numero_economico = models.CharField(
        "Número económico", max_length=20, blank=True, null=True, unique=True
    )
    nombre_completo = models.CharField("Nombre completo", max_length=255)
    correo_institucional = models.EmailField("Correo institucional", unique=True)
    departamento = models.ForeignKey(
        _DEPARTAMENTO,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profesores",
    )

    class Meta:
        verbose_name = "Profesor"
        verbose_name_plural = "Profesores"
        ordering = ["nombre_completo"]

    def __str__(self):
        return self.nombre_completo
