"""Modelos de catálogos institucionales de CyAD UAM Azcapotzalco."""

from django.db import models
from django.db.models import CheckConstraint, Q

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
    orden = models.PositiveSmallIntegerField("Orden", default=0)
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
        ordering = ["orden", "nombre"]

    def __str__(self):
        return f"{self.clave} — {self.nombre}"


class Posgrado(TimeStampedModel, EstadoActivoModel):
    """Posgrado ofrecido por CyAD (maestría, especialidad, doctorado)."""

    clave = models.CharField("Clave", max_length=20, unique=True)
    nombre = models.CharField("Nombre", max_length=200)
    orden = models.PositiveSmallIntegerField("Orden", default=0)
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posgrados",
    )

    class Meta:
        verbose_name = "Posgrado"
        verbose_name_plural = "Posgrados"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return f"{self.clave} — {self.nombre}"


class Area(TimeStampedModel, EstadoActivoModel):
    """Área curricular a la que pertenece una UEA (Licenciatura, optativas, etc.)."""

    nombre = models.CharField("Nombre", max_length=200)
    descripcion = models.CharField("Descripción", max_length=500, blank=True)

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
        unique_together = [("nombre", "descripcion")]
        ordering = ["nombre", "descripcion"]

    def __str__(self):
        return f"{self.nombre} — {self.descripcion}" if self.descripcion else self.nombre


class UEA(TimeStampedModel, EstadoActivoModel):
    """Unidad de Enseñanza-Aprendizaje (materia) del plan de estudios."""

    class Tipo(models.TextChoices):
        OBLIGATORIA = "OBL", "Obligatoria"
        OPTATIVA = "OPT", "Optativa"
        OTRO = "OTRO", "Otro"

    clave = models.CharField("Clave", max_length=20, unique=True)
    nombre = models.CharField("Nombre", max_length=300)
    licenciatura = models.ForeignKey(
        Licenciatura,
        on_delete=models.PROTECT,
        related_name="ueas",
        null=True,
        blank=True,
    )
    posgrado = models.ForeignKey(
        Posgrado,
        on_delete=models.PROTECT,
        related_name="ueas",
        null=True,
        blank=True,
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="ueas",
        null=True,
        blank=True,
    )
    # Acepta enteros (1-12) o rangos romanos (ej. "VII-XII") para optativas.
    trimestre = models.CharField("Trimestre", max_length=20, blank=True, default="")
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
        ordering = ["licenciatura", "posgrado", "trimestre", "nombre"]
        constraints = [
            CheckConstraint(
                condition=(
                    (Q(licenciatura__isnull=False) & Q(posgrado__isnull=True))
                    | (Q(licenciatura__isnull=True) & Q(posgrado__isnull=False))
                ),
                name="uea_xor_licenciatura_posgrado",
            ),
        ]

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
    def get_activo(cls, recurso, hoy=None):
        """Devuelve el Periodo activo para el recurso o None.

        Un periodo está "activo para crear/editar" si:
          - estado=True
          - flag del recurso = True

        `hoy` se acepta por compatibilidad con call-sites antiguos pero ya no
        se utiliza (la disponibilidad la decide únicamente el flag).
        """
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
