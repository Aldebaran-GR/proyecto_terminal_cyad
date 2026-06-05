"""Serializers del módulo Autoevaluación."""

from decimal import Decimal

from rest_framework import serializers

from .models import (
    Formulario,
    NivelDesempeno,
    OpcionPregunta,
    Pregunta,
    Respuesta,
    RespuestaPregunta,
    Seccion,
)


# ---------------------------------------------------------------------------
# Form builder — Admin
# ---------------------------------------------------------------------------


class OpcionPreguntaSerializer(serializers.ModelSerializer):
    """Opción con puntos — para el Admin."""

    class Meta:
        model = OpcionPregunta
        fields = ["id", "texto", "valor", "puntos", "orden"]


class OpcionPreguntaPublicSerializer(serializers.ModelSerializer):
    """Opción sin puntos — para el Profesor (evita conocer el peso durante la respuesta)."""

    class Meta:
        model = OpcionPregunta
        fields = ["id", "texto", "valor", "orden"]


class PreguntaSerializer(serializers.ModelSerializer):
    opciones = OpcionPreguntaSerializer(many=True, required=False)

    class Meta:
        model = Pregunta
        fields = [
            "id",
            "formulario",
            "seccion",
            "tipo",
            "texto",
            "ayuda",
            "obligatoria",
            "orden",
            "config",
            "opciones",
        ]

    def _save_opciones(self, pregunta, opciones_data):
        pregunta.opciones.all().delete()
        for op in opciones_data:
            OpcionPregunta.objects.create(pregunta=pregunta, **op)

    def create(self, validated_data):
        opciones_data = validated_data.pop("opciones", [])
        pregunta = Pregunta.objects.create(**validated_data)
        self._save_opciones(pregunta, opciones_data)
        return pregunta

    def update(self, instance, validated_data):
        opciones_data = validated_data.pop("opciones", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if opciones_data is not None:
            self._save_opciones(instance, opciones_data)
        return instance


class PreguntaPublicSerializer(serializers.ModelSerializer):
    """Pregunta para el Profesor — opciones sin puntos."""

    opciones = OpcionPreguntaPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Pregunta
        fields = [
            "id",
            "formulario",
            "seccion",
            "tipo",
            "texto",
            "ayuda",
            "obligatoria",
            "orden",
            "config",
            "opciones",
        ]


class SeccionSerializer(serializers.ModelSerializer):
    preguntas = PreguntaSerializer(many=True, read_only=True)

    class Meta:
        model = Seccion
        fields = ["id", "formulario", "titulo", "descripcion", "orden", "preguntas"]


class SeccionPublicSerializer(serializers.ModelSerializer):
    """Sección para el Profesor — preguntas sin puntos."""

    preguntas = PreguntaPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Seccion
        fields = ["id", "formulario", "titulo", "descripcion", "orden", "preguntas"]


# ---------------------------------------------------------------------------
# Niveles de desempeño — Admin
# ---------------------------------------------------------------------------


class NivelDesempenoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NivelDesempeno
        fields = [
            "id",
            "formulario",
            "nombre",
            "porcentaje_min",
            "porcentaje_max",
            "observacion",
            "color",
            "orden",
        ]

    def validate(self, attrs):
        pmin = attrs.get("porcentaje_min", getattr(self.instance, "porcentaje_min", None))
        pmax = attrs.get("porcentaje_max", getattr(self.instance, "porcentaje_max", None))
        if pmin is not None and pmax is not None and pmin >= pmax:
            raise serializers.ValidationError(
                "porcentaje_min debe ser menor que porcentaje_max."
            )
        if pmin is not None and (pmin < 0 or pmin > 100):
            raise serializers.ValidationError("porcentaje_min debe estar entre 0 y 100.")
        if pmax is not None and (pmax < 0 or pmax > 100):
            raise serializers.ValidationError("porcentaje_max debe estar entre 0 y 100.")
        return attrs


class NivelDesempenoResumenSerializer(serializers.ModelSerializer):
    """Versión compacta para incrustar en el resultado de una Respuesta."""

    class Meta:
        model = NivelDesempeno
        fields = ["id", "nombre", "porcentaje_min", "porcentaje_max", "observacion", "color"]


# ---------------------------------------------------------------------------
# Formulario — Admin (completo)
# ---------------------------------------------------------------------------


class FormularioSerializer(serializers.ModelSerializer):
    """Serializer completo para Admin: incluye secciones, preguntas, niveles y puntaje máximo."""

    secciones = SeccionSerializer(many=True, read_only=True)
    preguntas = PreguntaSerializer(many=True, read_only=True)
    niveles = NivelDesempenoSerializer(many=True, read_only=True)
    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)
    total_respuestas = serializers.SerializerMethodField()
    puntaje_maximo_posible = serializers.SerializerMethodField()

    class Meta:
        model = Formulario
        fields = [
            "id",
            "titulo",
            "descripcion",
            "periodo",
            "periodo_clave",
            "estado",
            "version",
            "una_respuesta_por_profesor",
            "created_by",
            "published_at",
            "closed_at",
            "secciones",
            "preguntas",
            "niveles",
            "total_respuestas",
            "puntaje_maximo_posible",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "version",
            "created_by",
            "published_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]

    def get_total_respuestas(self, obj):
        return obj.respuestas.filter(
            estado=Respuesta.Estado.ENVIADO,
            version_formulario=obj.version,
        ).count()

    def get_puntaje_maximo_posible(self, obj):
        """Suma del puntaje máximo alcanzable por tipo de pregunta."""
        total = Decimal("0")
        for pregunta in obj.preguntas.prefetch_related("opciones"):
            tipo = pregunta.tipo
            if tipo in Pregunta.TIPOS_NO_PUNTABLES:
                continue
            if tipo == Pregunta.Tipo.ESCALA_LINEAL:
                cfg = pregunta.config or {}
                factor = Decimal(str(cfg.get("puntos_factor", 1)))
                max_val = Decimal(str(cfg.get("max", 5)))
                total += max_val * factor
            elif tipo == Pregunta.Tipo.SI_NO:
                cfg = pregunta.config or {}
                pts_si = Decimal(str(cfg.get("puntos_si", 1)))
                pts_no = Decimal(str(cfg.get("puntos_no", 0)))
                total += max(pts_si, pts_no)
            elif tipo == Pregunta.Tipo.CASILLAS:
                total += sum(
                    op.puntos for op in pregunta.opciones.all() if op.puntos > 0
                )
            else:  # OPCION_UNICA, LISTA_DESPLEGABLE
                opts = list(pregunta.opciones.all())
                if opts:
                    total += max(op.puntos for op in opts)
        return float(total)


class FormularioListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados."""

    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)
    total_preguntas = serializers.SerializerMethodField()
    total_respuestas = serializers.SerializerMethodField()

    class Meta:
        model = Formulario
        fields = [
            "id",
            "titulo",
            "descripcion",
            "periodo",
            "periodo_clave",
            "estado",
            "version",
            "una_respuesta_por_profesor",
            "published_at",
            "closed_at",
            "total_preguntas",
            "total_respuestas",
            "created_at",
        ]

    def get_total_preguntas(self, obj):
        return obj.preguntas.count()

    def get_total_respuestas(self, obj):
        return obj.respuestas.filter(
            estado=Respuesta.Estado.ENVIADO,
            version_formulario=obj.version,
        ).count()


# ---------------------------------------------------------------------------
# Formularios disponibles — Profesor (lectura)
# ---------------------------------------------------------------------------


class FormularioDisponibleSerializer(serializers.ModelSerializer):
    """Formularios publicados visibles para el profesor autenticado.

    - ya_respondido: True solo si tiene respuesta ENVIADO en la versión actual.
    - respuesta_id: ID de la respuesta de la versión actual (borrador o enviada).
    - version: versión actual del formulario — si cambió tras la última respuesta
      del profesor, ya_respondido será False y necesita volver a contestar.
    """

    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)
    ya_respondido = serializers.SerializerMethodField()
    respuesta_id = serializers.SerializerMethodField()
    respuesta_estado = serializers.SerializerMethodField()
    total_preguntas = serializers.SerializerMethodField()
    secciones = SeccionPublicSerializer(many=True, read_only=True)
    preguntas = PreguntaPublicSerializer(many=True, read_only=True)
    niveles = NivelDesempenoResumenSerializer(many=True, read_only=True)
    puntaje_maximo_posible = serializers.SerializerMethodField()

    class Meta:
        model = Formulario
        fields = [
            "id",
            "titulo",
            "descripcion",
            "periodo",
            "periodo_clave",
            "estado",
            "version",
            "published_at",
            "total_preguntas",
            "ya_respondido",
            "respuesta_id",
            "respuesta_estado",
            "secciones",
            "preguntas",
            "niveles",
            "puntaje_maximo_posible",
        ]

    def _get_respuesta_actual(self, obj):
        """Devuelve la respuesta del profesor a la versión actual del formulario."""
        request = self.context.get("request")
        if not request or not getattr(request.user, "es_profesor", False):
            return None
        try:
            return obj.respuestas.get(
                profesor=request.user.perfil_profesor,
                version_formulario=obj.version,
            )
        except Respuesta.DoesNotExist:
            return None

    def get_ya_respondido(self, obj):
        r = self._get_respuesta_actual(obj)
        return r is not None and r.estado == Respuesta.Estado.ENVIADO

    def get_respuesta_id(self, obj):
        r = self._get_respuesta_actual(obj)
        return r.id if r else None

    def get_respuesta_estado(self, obj):
        r = self._get_respuesta_actual(obj)
        return r.estado if r else None

    def get_total_preguntas(self, obj):
        return obj.preguntas.count()

    def get_puntaje_maximo_posible(self, obj):
        total = Decimal("0")
        for pregunta in obj.preguntas.prefetch_related("opciones"):
            tipo = pregunta.tipo
            if tipo in Pregunta.TIPOS_NO_PUNTABLES:
                continue
            if tipo == Pregunta.Tipo.ESCALA_LINEAL:
                cfg = pregunta.config or {}
                factor = Decimal(str(cfg.get("puntos_factor", 1)))
                max_val = Decimal(str(cfg.get("max", 5)))
                total += max_val * factor
            elif tipo == Pregunta.Tipo.SI_NO:
                cfg = pregunta.config or {}
                pts_si = Decimal(str(cfg.get("puntos_si", 1)))
                pts_no = Decimal(str(cfg.get("puntos_no", 0)))
                total += max(pts_si, pts_no)
            elif tipo == Pregunta.Tipo.CASILLAS:
                total += sum(
                    op.puntos for op in pregunta.opciones.all() if op.puntos > 0
                )
            else:
                opts = list(pregunta.opciones.all())
                if opts:
                    total += max(op.puntos for op in opts)
        return float(total)


# ---------------------------------------------------------------------------
# Respuestas — Profesor
# ---------------------------------------------------------------------------


class RespuestaPreguntaSerializer(serializers.ModelSerializer):
    opciones_seleccionadas = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=OpcionPregunta.objects.all(),
        required=False,
    )

    class Meta:
        model = RespuestaPregunta
        fields = ["id", "pregunta", "valor_texto", "opciones_seleccionadas"]


class RespuestaSerializer(serializers.ModelSerializer):
    items = RespuestaPreguntaSerializer(many=True, required=False)
    formulario_titulo = serializers.CharField(source="formulario.titulo", read_only=True)
    profesor_nombre = serializers.CharField(
        source="profesor.nombre_completo", read_only=True
    )
    nivel_desempeno = NivelDesempenoResumenSerializer(read_only=True)

    class Meta:
        model = Respuesta
        fields = [
            "id",
            "formulario",
            "formulario_titulo",
            "profesor",
            "profesor_nombre",
            "version_formulario",
            "estado",
            "enviado_at",
            "puntaje_obtenido",
            "puntaje_maximo",
            "porcentaje",
            "nivel_desempeno",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "profesor",
            "version_formulario",
            "estado",
            "enviado_at",
            "puntaje_obtenido",
            "puntaje_maximo",
            "porcentaje",
            "nivel_desempeno",
            "created_at",
            "updated_at",
        ]

    def validate_formulario(self, formulario):
        if formulario.estado != Formulario.Estado.PUBLICADO:
            raise serializers.ValidationError(
                "Solo se puede responder un formulario en estado PUBLICADO."
            )
        return formulario

    def _save_items(self, respuesta, items_data):
        respuesta.items.all().delete()
        for item_data in items_data:
            opciones = item_data.pop("opciones_seleccionadas", [])
            rp = RespuestaPregunta.objects.create(respuesta=respuesta, **item_data)
            if opciones:
                rp.opciones_seleccionadas.set(opciones)

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        respuesta = Respuesta.objects.create(**validated_data)
        self._save_items(respuesta, items_data)
        return respuesta

    def update(self, instance, validated_data):
        if instance.estado == Respuesta.Estado.ENVIADO:
            raise serializers.ValidationError(
                "No se puede modificar una respuesta ya enviada."
            )
        items_data = validated_data.pop("items", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if items_data is not None:
            self._save_items(instance, items_data)
        return instance


# ---------------------------------------------------------------------------
# Estadísticas — Admin
# ---------------------------------------------------------------------------


class EstadisticaOpcionSerializer(serializers.Serializer):
    opcion_id = serializers.IntegerField()
    texto = serializers.CharField()
    puntos = serializers.FloatField()
    conteo = serializers.IntegerField()


class EstadisticaPreguntaSerializer(serializers.Serializer):
    pregunta_id = serializers.IntegerField()
    texto = serializers.CharField()
    tipo = serializers.CharField()
    puntable = serializers.BooleanField()
    total_respuestas = serializers.IntegerField()
    opciones = EstadisticaOpcionSerializer(many=True)
    promedio = serializers.FloatField(allow_null=True)
