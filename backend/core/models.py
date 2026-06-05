"""Modelos base reutilizables para todas las apps."""

from django.db import models


class TimeStampedModel(models.Model):
    """Agrega marcas de tiempo de creación y actualización."""

    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class EstadoActivoModel(models.Model):
    """Agrega un indicador de estado activo/inactivo (borrado lógico)."""

    estado = models.BooleanField("Activo", default=True)

    class Meta:
        abstract = True
