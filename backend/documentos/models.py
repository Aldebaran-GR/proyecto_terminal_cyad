"""Modelos de documentos académicos: Carta Temática y Requisitos de Recuperación.

Después del rediseño de junio 2026:
- Ambos documentos son **planos**: campos de texto libre, sin sub-modelos.
- Las antiguas tablas Tema/Subtema/Bibliografia/CriterioEvaluacion (Carta Temática)
  y RequisitoItem (Requisitos) fueron eliminadas.
"""

from django.db import models

from core.models import TimeStampedModel


class DocumentoAcademicoBase(TimeStampedModel):
    """Campos comunes a todos los documentos académicos.

    Estados:
      BORRADOR  → editable; no visible públicamente
      PUBLICADO → publicado al espacio público; no editable hasta despublicar
    """

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PUBLICADO = "PUBLICADO", "Publicado"

    class Modalidad(models.TextChoices):
        PRESENCIAL = "PRESENCIAL", "Presencial"
        REMOTO = "REMOTO", "Remoto"
        MIXTO = "MIXTO", "Mixto"

    # SET_NULL: si el profesor es eliminado, el documento se conserva como
    # historial. Los snapshots de nombre y correo (abajo) preservan a
    # quién pertenecía aunque el FK se haya nullificado.
    profesor = models.ForeignKey(
        "accounts.Profesor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_set",
    )
    # Snapshot del profesor al momento de crear el documento. Se llena
    # automáticamente desde DocumentoMixin.perform_create y se preserva
    # aunque el Profesor sea eliminado.
    profesor_nombre = models.CharField(
        "Nombre del profesor (histórico)", max_length=255, blank=True,
    )
    profesor_correo = models.EmailField(
        "Correo del profesor (histórico)", blank=True,
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
        """Solo se edita en BORRADOR. Para modificar un doc PUBLICADO,
        despublícalo primero (cambiar-estado → BORRADOR)."""
        return self.estado == self.Estado.BORRADOR

    def puede_eliminar(self):
        return self.estado == self.Estado.BORRADOR


# ---------------------------------------------------------------------------
# Carta Temática
# ---------------------------------------------------------------------------

class CartaTematica(DocumentoAcademicoBase):
    """Carta temática de una UEA para un grupo y periodo dados.

    Todos los campos de contenido son TextField libre para que el profesor
    los redacte como prefiera. La vista pública los muestra como bloques.
    """

    descripcion_uea = models.TextField("Descripción de la UEA", blank=True)
    objetivo_general = models.TextField("Objetivo general", blank=True)
    objetivos_particulares = models.TextField("Objetivos particulares", blank=True)
    contenido_sintetico = models.TextField("Contenido sintético", blank=True)
    objetivos_aprendizaje = models.TextField("Objetivos de aprendizaje", blank=True)
    requerimientos = models.TextField(
        "Requerimientos", blank=True,
        help_text="Materiales y herramientas necesarios.",
    )
    conocimientos_previos = models.TextField("Conocimientos previos", blank=True)
    modalidad_evaluacion = models.TextField("Modalidad de evaluación", blank=True)
    revisiones_asesorias = models.TextField("Revisiones / asesorías", blank=True)
    bibliografia = models.TextField("Bibliografía", blank=True)
    calendarizacion_actividades = models.TextField(
        "Calendarización de actividades", blank=True,
    )

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


# ---------------------------------------------------------------------------
# Requisitos de Recuperación
# ---------------------------------------------------------------------------

class RequisitoRecuperacion(DocumentoAcademicoBase):
    """Documento de "Evaluación de Recuperación" para una UEA y grupo.

    Es un documento plano de texto libre — los campos antes normalizados
    (`espacio_modalidad`, `indicaciones`, `RequisitoItem`) fueron eliminados.
    """

    lugar = models.TextField(
        "Lugar", blank=True,
        help_text=(
            "Texto libre. Si es remoto, puede incluir liga y contraseña."
        ),
    )
    duracion_aprox = models.CharField(
        "Duración aproximada", max_length=100, blank=True,
    )
    fecha_hora = models.CharField(
        "Fecha y hora", max_length=100, blank=True,
        help_text="Texto libre, ej. 'Lunes 15 de mayo, 10:00 h'.",
    )
    recursos_necesarios = models.TextField(
        "Recursos necesarios", blank=True,
        help_text="Materiales, herramientas, etc.",
    )
    requisitos = models.TextField(
        "Requisitos", blank=True,
        help_text="Investigación, maqueta, % de tareas entregadas, etc.",
    )
    notas = models.TextField("Notas", blank=True)

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
