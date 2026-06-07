"""Modelos del módulo Autoevaluación: form builder + respuestas + scoring + versionado."""

from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class Formulario(TimeStampedModel):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PUBLICADO = "PUBLICADO", "Publicado"
        CERRADO = "CERRADO", "Cerrado"

    titulo = models.CharField("Título", max_length=255)
    descripcion = models.TextField("Descripción", blank=True)
    periodo = models.ForeignKey(
        "catalogos.Periodo",
        on_delete=models.PROTECT,
        related_name="formularios",
        verbose_name="Periodo",
    )
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.BORRADOR
    )
    # Versión: se incrementa cada vez que el admin publica una revisión.
    # Las respuestas guardan la versión que contestaron; "ya respondió la versión actual"
    # se evalúa comparando Respuesta.version_formulario con Formulario.version.
    version = models.PositiveIntegerField("Versión", default=1)
    una_respuesta_por_profesor = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "accounts.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Creado por",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Formulario"
        verbose_name_plural = "Formularios"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.titulo} v{self.version} ({self.get_estado_display()})"

    def publicar(self):
        if self.estado != self.Estado.BORRADOR:
            raise ValueError("Solo se puede publicar un formulario en estado BORRADOR.")
        self.estado = self.Estado.PUBLICADO
        self.published_at = timezone.now()
        self.save(update_fields=["estado", "published_at"])

    def cerrar(self):
        if self.estado != self.Estado.PUBLICADO:
            raise ValueError("Solo se puede cerrar un formulario en estado PUBLICADO.")
        self.estado = self.Estado.CERRADO
        self.closed_at = timezone.now()
        self.save(update_fields=["estado", "closed_at"])

    def despublicar(self):
        """Regresa el formulario a BORRADOR para poder editarlo de nuevo.

        Acepta tanto PUBLICADO como CERRADO. Las respuestas existentes se
        conservan. La versión no se incrementa: si el admin re-publica,
        es el mismo formulario.
        """
        if self.estado not in (self.Estado.PUBLICADO, self.Estado.CERRADO):
            raise ValueError(
                "Solo se puede despublicar un formulario PUBLICADO o CERRADO."
            )
        self.estado = self.Estado.BORRADOR
        # Conservamos `published_at` como timestamp de la última publicación
        # para auditoría; el siguiente publicar() lo refresca.
        self.save(update_fields=["estado"])

    def reabrir(self):
        """CERRADO → PUBLICADO sin incrementar versión.

        Útil si el admin cierra anticipadamente por error y quiere volver a
        aceptar respuestas sin obligar a re-responder a quienes ya enviaron.
        """
        if self.estado != self.Estado.CERRADO:
            raise ValueError("Solo se puede reabrir un formulario CERRADO.")
        self.estado = self.Estado.PUBLICADO
        self.published_at = timezone.now()
        self.closed_at = None
        self.save(update_fields=["estado", "published_at", "closed_at"])

    def publicar_revision(self):
        """Incrementa la versión y vuelve a publicar el formulario desde CERRADO.

        Todos los profesores (respondieron v_anterior o no) verán el formulario
        como pendiente porque su respuesta tiene version_formulario < version actual.
        Las respuestas anteriores se conservan como historial.
        """
        if self.estado != self.Estado.CERRADO:
            raise ValueError(
                "Solo se puede publicar una revisión de un formulario CERRADO."
            )
        self.version += 1
        self.estado = self.Estado.PUBLICADO
        self.published_at = timezone.now()
        self.save(update_fields=["version", "estado", "published_at"])


class Seccion(models.Model):
    formulario = models.ForeignKey(
        Formulario, on_delete=models.CASCADE, related_name="secciones"
    )
    titulo = models.CharField("Título", max_length=255)
    descripcion = models.TextField("Descripción", blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden"]
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"

    def __str__(self):
        return f"{self.formulario} — {self.titulo}"


class Pregunta(models.Model):
    class Tipo(models.TextChoices):
        TEXTO_CORTO = "TEXTO_CORTO", "Texto corto"
        TEXTO_LARGO = "TEXTO_LARGO", "Texto largo"
        OPCION_UNICA = "OPCION_UNICA", "Opción única"
        CASILLAS = "CASILLAS", "Casillas de verificación"
        SI_NO = "SI_NO", "Sí / No"
        ESCALA_LINEAL = "ESCALA_LINEAL", "Escala lineal"
        LISTA_DESPLEGABLE = "LISTA_DESPLEGABLE", "Lista desplegable"

    # Tipos cuyas respuestas no contribuyen al puntaje (respuesta cualitativa abierta)
    TIPOS_NO_PUNTABLES = {"TEXTO_CORTO", "TEXTO_LARGO"}

    formulario = models.ForeignKey(
        Formulario, on_delete=models.CASCADE, related_name="preguntas"
    )
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preguntas",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    texto = models.TextField("Texto de la pregunta")
    ayuda = models.CharField("Texto de ayuda", max_length=500, blank=True)
    obligatoria = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)
    # JSON por tipo:
    #   ESCALA_LINEAL  → {min, max, label_min, label_max, puntos_factor}
    #                    score = valor_seleccionado × puntos_factor  (default factor=1)
    #   SI_NO          → {puntos_si, puntos_no}  (default: si=1, no=0)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["orden"]
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.texto[:60]}"

    def tiene_opciones(self):
        return self.tipo in (
            self.Tipo.OPCION_UNICA,
            self.Tipo.CASILLAS,
            self.Tipo.LISTA_DESPLEGABLE,
        )

    def es_puntable(self):
        """Indica si esta pregunta contribuye al puntaje total del formulario."""
        return self.tipo not in self.TIPOS_NO_PUNTABLES


class OpcionPregunta(models.Model):
    pregunta = models.ForeignKey(
        Pregunta, on_delete=models.CASCADE, related_name="opciones"
    )
    texto = models.CharField(max_length=255)
    valor = models.CharField(max_length=100, blank=True)
    # Puntos que suma esta opción al puntaje del profesor al seleccionarla.
    # Para CASILLAS se suman todas las opciones seleccionadas.
    # Para OPCION_UNICA / LISTA_DESPLEGABLE solo la opción elegida.
    puntos = models.DecimalField("Puntos", max_digits=5, decimal_places=2, default=0)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden"]
        verbose_name = "Opción"
        verbose_name_plural = "Opciones"

    def __str__(self):
        return f"{self.texto} ({self.puntos} pts)"


class NivelDesempeno(models.Model):
    """Rango porcentual con observación cualitativa. El Admin define uno o más
    niveles por formulario; al enviar la respuesta el sistema asigna el nivel
    cuyo rango incluye el porcentaje obtenido por el profesor."""

    formulario = models.ForeignKey(
        Formulario,
        on_delete=models.CASCADE,
        related_name="niveles",
        verbose_name="Formulario",
    )
    nombre = models.CharField("Nombre", max_length=100)
    porcentaje_min = models.DecimalField(
        "% mínimo", max_digits=5, decimal_places=2,
        help_text="Porcentaje mínimo (0–100) para este nivel."
    )
    porcentaje_max = models.DecimalField(
        "% máximo", max_digits=5, decimal_places=2,
        help_text="Porcentaje máximo (0–100) para este nivel."
    )
    observacion = models.TextField("Observación")
    color = models.CharField(
        "Color", max_length=20, default="gray",
        help_text="Clave para la UI: green | blue | yellow | red | gray"
    )
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "porcentaje_min"]
        verbose_name = "Nivel de desempeño"
        verbose_name_plural = "Niveles de desempeño"

    def __str__(self):
        return f"{self.nombre} ({self.porcentaje_min}%–{self.porcentaje_max}%)"


class Respuesta(TimeStampedModel):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ENVIADO = "ENVIADO", "Enviado"

    formulario = models.ForeignKey(
        Formulario, on_delete=models.PROTECT, related_name="respuestas"
    )
    profesor = models.ForeignKey(
        "accounts.Profesor",
        on_delete=models.PROTECT,
        related_name="respuestas_formulario",
    )
    # Versión del formulario en el momento de la respuesta. La unicidad es
    # (formulario, profesor, version_formulario) → al incrementar la versión
    # el profesor puede volver a responder sin violar el constraint.
    version_formulario = models.PositiveIntegerField("Versión del formulario", default=1)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.BORRADOR
    )
    enviado_at = models.DateTimeField(null=True, blank=True)

    # Puntaje — se calcula y persiste al enviar; null mientras está en borrador.
    puntaje_obtenido = models.DecimalField(
        "Puntaje obtenido", max_digits=7, decimal_places=2, null=True, blank=True
    )
    puntaje_maximo = models.DecimalField(
        "Puntaje máximo posible", max_digits=7, decimal_places=2, null=True, blank=True
    )
    porcentaje = models.DecimalField(
        "Porcentaje (%)", max_digits=5, decimal_places=2, null=True, blank=True
    )
    nivel_desempeno = models.ForeignKey(
        NivelDesempeno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="respuestas",
        verbose_name="Nivel de desempeño",
    )

    class Meta:
        verbose_name = "Respuesta"
        verbose_name_plural = "Respuestas"
        constraints = [
            models.UniqueConstraint(
                fields=["formulario", "profesor", "version_formulario"],
                name="unique_respuesta_formulario_profesor_version",
            )
        ]

    def __str__(self):
        return (
            f"Respuesta v{self.version_formulario} de {self.profesor} "
            f"a {self.formulario}"
        )


class RespuestaPregunta(models.Model):
    respuesta = models.ForeignKey(
        Respuesta, on_delete=models.CASCADE, related_name="items"
    )
    pregunta = models.ForeignKey(
        Pregunta, on_delete=models.PROTECT, related_name="respuestas_recibidas"
    )
    valor_texto = models.TextField(blank=True)
    opciones_seleccionadas = models.ManyToManyField(
        OpcionPregunta, blank=True, related_name="selecciones"
    )

    class Meta:
        unique_together = [["respuesta", "pregunta"]]
        verbose_name = "Item de respuesta"
        verbose_name_plural = "Items de respuesta"
