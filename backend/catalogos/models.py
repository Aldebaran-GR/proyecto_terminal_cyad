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
    # Liga oficial a la página de la UEA (opcional). Se muestra en la vista
    # pública de Cartas Temáticas asociadas a esta UEA.
    liga = models.URLField("Liga / página oficial", max_length=500, blank=True)

    class Meta:
        verbose_name = "UEA"
        verbose_name_plural = "UEA"
        ordering = ["licenciatura", "trimestre", "nombre"]

    def __str__(self):
        return f"{self.clave} — {self.nombre}"


class Periodo(TimeStampedModel):
    """Periodo académico trimestral (ej. 24-I, 24-P, 24-O).

    A diferencia de un único flag "activo", un periodo puede estar activo de
    forma independiente para cada tipo de recurso:
      - Cartas Temáticas
      - Requisitos de Recuperación
      - Autoevaluación

    Esto refleja el ciclo real CyAD: durante el trimestre N suelen estar abiertos
    requisitos y autoevaluación del trimestre N, pero las cartas temáticas que
    los profesores preparan corresponden al siguiente trimestre N+1.

    La restricción de unicidad es por flag (a lo más un Periodo con cada flag).
    """

    class Recurso(models.TextChoices):
        CARTAS = "CARTAS", "Cartas Temáticas"
        REQUISITOS = "REQUISITOS", "Requisitos de Recuperación"
        AUTOEVALUACION = "AUTOEVALUACION", "Autoevaluación"

    _RECURSO_FIELD = {
        Recurso.CARTAS: "activo_cartas",
        Recurso.REQUISITOS: "activo_requisitos",
        Recurso.AUTOEVALUACION: "activo_autoevaluacion",
    }

    clave = models.CharField("Clave", max_length=10, unique=True)
    fecha_inicio = models.DateField("Fecha de inicio")
    fecha_fin = models.DateField("Fecha de fin")
    # Flags por recurso — el activo se decide individualmente por cada uno.
    activo_cartas = models.BooleanField("Activo para Cartas Temáticas", default=False)
    activo_requisitos = models.BooleanField("Activo para Requisitos de Recuperación", default=False)
    activo_autoevaluacion = models.BooleanField("Activo para Autoevaluación", default=False)
    # Flag legado: True si el periodo está activo para CUALQUIER recurso.
    # Se mantiene sincronizado en save() para no romper queries antiguas.
    activo = models.BooleanField("Activo (cualquier recurso)", default=False, editable=False)
    estado = models.BooleanField("Habilitado", default=True)

    class Meta:
        verbose_name = "Periodo"
        verbose_name_plural = "Periodos"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return self.clave

    # ── Helpers ──────────────────────────────────────────────────────────
    @classmethod
    def get_activo(cls, recurso):
        """Devuelve el Periodo activo para el recurso indicado (o None)."""
        field = cls._RECURSO_FIELD.get(recurso)
        if not field:
            return None
        return cls.objects.filter(**{field: True, "estado": True}).first()

    def save(self, *args, **kwargs):
        """Garantiza unicidad por recurso: solo un Periodo con cada flag en True.
        Mantiene `activo` (legado) sincronizado como OR de los tres flags,
        incluyendo en los periodos a los que se les apaga algún flag.
        """
        per_resource_fields = ("activo_cartas", "activo_requisitos", "activo_autoevaluacion")
        afectados = set()
        for field in per_resource_fields:
            if getattr(self, field):
                qs = Periodo.objects.exclude(pk=self.pk).filter(**{field: True})
                afectados.update(qs.values_list("pk", flat=True))
                qs.update(**{field: False})
        # Recomputa `activo` en los periodos a los que les bajamos algún flag
        # (update() bypassea save(), así que lo hacemos manualmente).
        for p in Periodo.objects.filter(pk__in=afectados):
            nuevo_activo = any(getattr(p, f) for f in per_resource_fields)
            if p.activo != nuevo_activo:
                Periodo.objects.filter(pk=p.pk).update(activo=nuevo_activo)
        self.activo = any(getattr(self, f) for f in per_resource_fields)
        super().save(*args, **kwargs)
