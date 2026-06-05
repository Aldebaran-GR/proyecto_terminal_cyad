"""Modelos de documentos académicos: Carta Temática y Requisitos de Recuperación."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import TimeStampedModel


class DocumentoAcademicoBase(TimeStampedModel):
    """Campos comunes a todos los documentos académicos."""

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PUBLICADO = "PUBLICADO", "Publicado"
        ENVIADO = "ENVIADO", "Enviado"

    class Modalidad(models.TextChoices):
        PRESENCIAL = "PRESENCIAL", "Presencial"
        REMOTO = "REMOTO", "Remoto"
        MIXTO = "MIXTO", "Mixto"

    profesor = models.ForeignKey(
        "accounts.Profesor",
        on_delete=models.PROTECT,
        related_name="%(class)s_set",
    )
    uea = models.ForeignKey(
        "catalogos.UEA",
        on_delete=models.PROTECT,
        related_name="%(class)s_set",
    )
    periodo = models.ForeignKey(
        "catalogos.Periodo",
        on_delete=models.PROTECT,
        related_name="%(class)s_set",
    )
    nombre_grupo = models.CharField("Nombre del grupo", max_length=100)
    id_grupo = models.CharField("ID del grupo", max_length=50)
    horario = models.CharField("Horario", max_length=100)
    modalidad = models.CharField(
        "Modalidad", max_length=12, choices=Modalidad.choices, blank=True
    )
    estado = models.CharField(
        "Estado", max_length=10, choices=Estado.choices, default=Estado.BORRADOR
    )

    class Meta:
        abstract = True

    def puede_editar(self):
        """Solo se puede editar si no ha sido enviado."""
        return self.estado != self.Estado.ENVIADO

    def puede_eliminar(self):
        return self.estado == self.Estado.BORRADOR


# ---------------------------------------------------------------------------
# Carta Temática
# ---------------------------------------------------------------------------

class CartaTematica(DocumentoAcademicoBase):
    """Carta temática de una UEA para un grupo y periodo dados."""

    objetivo_general = models.TextField("Objetivo general", blank=True)
    presentacion = models.TextField("Presentación", blank=True)

    class Meta:
        verbose_name = "Carta Temática"
        verbose_name_plural = "Cartas Temáticas"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["profesor", "periodo", "uea", "id_grupo"],
                name="unique_carta_profesor_periodo_uea_grupo",
            )
        ]

    def __str__(self):
        return f"CT | {self.uea} | {self.nombre_grupo} | {self.periodo}"


class Tema(models.Model):
    """Tema de una Carta Temática."""

    carta = models.ForeignKey(
        CartaTematica, on_delete=models.CASCADE, related_name="temas"
    )
    orden = models.PositiveSmallIntegerField("Orden", default=1)
    nombre = models.CharField("Nombre del tema", max_length=300)
    objetivo = models.TextField("Objetivo del tema", blank=True)
    num_sesiones = models.PositiveSmallIntegerField("Número de sesiones", default=1)

    class Meta:
        ordering = ["orden"]

    def __str__(self):
        return f"{self.orden}. {self.nombre}"


class Subtema(models.Model):
    """Subtema dentro de un Tema."""

    tema = models.ForeignKey(Tema, on_delete=models.CASCADE, related_name="subtemas")
    orden = models.PositiveSmallIntegerField("Orden", default=1)
    descripcion = models.CharField("Descripción", max_length=500)

    class Meta:
        ordering = ["orden"]

    def __str__(self):
        return self.descripcion


class Bibliografia(models.Model):
    """Referencia bibliográfica de una Carta Temática."""

    class Tipo(models.TextChoices):
        BASICA = "BASICA", "Básica"
        COMPLEMENTARIA = "COMPLEMENTARIA", "Complementaria"

    carta = models.ForeignKey(
        CartaTematica, on_delete=models.CASCADE, related_name="bibliografias"
    )
    tipo = models.CharField("Tipo", max_length=15, choices=Tipo.choices, default=Tipo.BASICA)
    referencia = models.TextField("Referencia")

    class Meta:
        ordering = ["tipo", "id"]


class CriterioEvaluacion(models.Model):
    """Criterio de evaluación con ponderación porcentual."""

    carta = models.ForeignKey(
        CartaTematica, on_delete=models.CASCADE, related_name="criterios"
    )
    descripcion = models.CharField("Descripción", max_length=300)
    ponderacion = models.PositiveSmallIntegerField(
        "Ponderación (%)",
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )

    class Meta:
        ordering = ["-ponderacion"]


# ---------------------------------------------------------------------------
# Requisitos de Recuperación
# ---------------------------------------------------------------------------

class RequisitoRecuperacion(DocumentoAcademicoBase):
    """Documento de requisitos de recuperación para una UEA y grupo."""

    espacio_modalidad = models.CharField(
        "Espacio / Modalidad",
        max_length=12,
        choices=DocumentoAcademicoBase.Modalidad.choices,
        blank=True,
    )
    indicaciones = models.TextField("Indicaciones de recuperación", blank=True)

    class Meta:
        verbose_name = "Requisito de Recuperación"
        verbose_name_plural = "Requisitos de Recuperación"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["profesor", "periodo", "uea", "id_grupo"],
                name="unique_requisito_profesor_periodo_uea_grupo",
            )
        ]

    def __str__(self):
        return f"RR | {self.uea} | {self.nombre_grupo} | {self.periodo}"


class RequisitoItem(models.Model):
    """Ítem individual dentro de un Requisito de Recuperación."""

    requisito = models.ForeignKey(
        RequisitoRecuperacion, on_delete=models.CASCADE, related_name="items"
    )
    orden = models.PositiveSmallIntegerField("Orden", default=1)
    descripcion = models.CharField("Descripción", max_length=500)

    class Meta:
        ordering = ["orden"]
