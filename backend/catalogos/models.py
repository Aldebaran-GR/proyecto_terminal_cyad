"""Modelos de catálogos institucionales de CyAD UAM Azcapotzalco."""

from django.db import models

from core.models import EstadoActivoModel, TimeStampedModel


class Departamento(TimeStampedModel, EstadoActivoModel):
    """Departamento académico de CyAD."""

    clave = models.CharField("Clave", max_length=20, unique=True)
    nombre = models.CharField("Nombre", max_length=200)

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.clave} — {self.nombre}"


class Licenciatura(TimeStampedModel, EstadoActivoModel):
    """Licenciatura ofrecida por CyAD."""

    clave = models.CharField("Clave", max_length=20, unique=True)
    nombre = models.CharField("Nombre", max_length=200)
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="licenciaturas",
    )

    class Meta:
        verbose_name = "Licenciatura"
        verbose_name_plural = "Licenciaturas"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.clave} — {self.nombre}"


class UEA(TimeStampedModel, EstadoActivoModel):
    """Unidad de Enseñanza-Aprendizaje (materia) del plan de estudios."""

    class Tipo(models.TextChoices):
        OBLIGATORIA = "OBL", "Obligatoria"
        OPTATIVA = "OPT", "Optativa"
        OTRO = "OTRO", "Otro"

    class Etapa(models.TextChoices):
        TRONCO_GENERAL = "TG", "Tronco General"
        TRONCO_BASICO = "TB", "Tronco Básico Profesional"
        TRONCO_INTEGRACION = "TI", "Tronco de Integración"

    clave = models.CharField("Clave", max_length=20, unique=True)
    nombre = models.CharField("Nombre", max_length=300)
    licenciatura = models.ForeignKey(
        Licenciatura,
        on_delete=models.PROTECT,
        related_name="ueas",
    )
    trimestre = models.PositiveSmallIntegerField("Trimestre", null=True, blank=True)
    etapa = models.CharField(
        "Etapa formativa", max_length=4, choices=Etapa.choices, blank=True
    )
    tipo = models.CharField(
        "Tipo", max_length=4, choices=Tipo.choices, default=Tipo.OBLIGATORIA
    )
    creditos = models.PositiveSmallIntegerField("Créditos", null=True, blank=True)

    class Meta:
        verbose_name = "UEA"
        verbose_name_plural = "UEA"
        ordering = ["licenciatura", "trimestre", "nombre"]

    def __str__(self):
        return f"{self.clave} — {self.nombre}"


class Periodo(TimeStampedModel):
    """Periodo académico trimestral (ej. 24-I, 24-P, 24-O)."""

    clave = models.CharField("Clave", max_length=10, unique=True)
    fecha_inicio = models.DateField("Fecha de inicio")
    fecha_fin = models.DateField("Fecha de fin")
    activo = models.BooleanField("Periodo activo", default=False)
    estado = models.BooleanField("Habilitado", default=True)

    class Meta:
        verbose_name = "Periodo"
        verbose_name_plural = "Periodos"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return self.clave

    def save(self, *args, **kwargs):
        """Garantiza que solo exista un periodo activo a la vez."""
        if self.activo:
            Periodo.objects.exclude(pk=self.pk).filter(activo=True).update(activo=False)
        super().save(*args, **kwargs)
