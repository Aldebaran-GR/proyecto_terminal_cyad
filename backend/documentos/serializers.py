"""Serializers de documentos académicos.

Después del rediseño los documentos son planos (sin sub-modelos): solo campos
de texto libre. Esto simplifica drásticamente create/update.

Adicionalmente, se exponen dos serializers de **vista pública** que devuelven
solo los campos seguros (sin IDs internos del usuario) y un campo
`tipo_documento` constante para que la UI pública lo muestre como título.
"""

from rest_framework import serializers

from .models import CartaTematica, RequisitoRecuperacion


def _profesor_nombre(obj):
    """Nombre del profesor: vivo si aún existe, snapshot si fue eliminado."""
    if obj.profesor and obj.profesor.nombre_completo:
        return obj.profesor.nombre_completo
    return obj.profesor_nombre or ""


def _profesor_correo(obj):
    if obj.profesor and obj.profesor.correo_institucional:
        return obj.profesor.correo_institucional
    return obj.profesor_correo or ""


# ---------------------------------------------------------------------------
# Carta Temática
# ---------------------------------------------------------------------------

class CartaTematicaSerializer(serializers.ModelSerializer):
    """Serializer interno (profesor / admin) — incluye todos los campos.

    `profesor_nombre` y `profesor_correo` usan el snapshot si el FK del
    profesor está vacío (profesor eliminado), garantizando que el
    histórico siga siendo legible.
    """

    profesor_nombre = serializers.SerializerMethodField()
    profesor_correo = serializers.SerializerMethodField()
    uea_nombre = serializers.CharField(source="uea.nombre", read_only=True)
    uea_clave = serializers.CharField(source="uea.clave", read_only=True)
    uea_liga = serializers.CharField(source="uea.liga", read_only=True)
    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)

    def get_profesor_nombre(self, obj):
        return _profesor_nombre(obj)

    def get_profesor_correo(self, obj):
        return _profesor_correo(obj)

    class Meta:
        model = CartaTematica
        fields = [
            "id", "profesor", "profesor_nombre", "profesor_correo",
            "uea", "uea_nombre", "uea_clave", "uea_liga",
            "periodo", "periodo_clave",
            "nombre_grupo", "id_grupo", "horario", "modalidad",
            # Contenido (10 campos de texto libre)
            "descripcion_uea", "objetivo_general", "objetivos_particulares",
            "contenido_sintetico", "objetivos_aprendizaje", "requerimientos",
            "conocimientos_previos", "modalidad_evaluacion",
            "revisiones_asesorias", "bibliografia", "calendarizacion_actividades",
            "estado",
            "created_at", "updated_at",
        ]
        # `periodo` lo asigna el ViewSet (auto desde el periodo activo).
        read_only_fields = ["id", "profesor", "periodo", "created_at", "updated_at"]

    def validate(self, attrs):
        # Solo se puede editar mientras esté en BORRADOR. Si el profesor quiere
        # cambiar una carta PUBLICADA, primero debe despublicarla (cambiar-estado
        # → BORRADOR). Esto fuerza el flujo "bajar del espacio público antes de
        # editar".
        if self.instance and self.instance.estado != CartaTematica.Estado.BORRADOR:
            raise serializers.ValidationError(
                "Solo se pueden editar documentos en BORRADOR. "
                "Despublica la carta primero."
            )
        return attrs


# ---------------------------------------------------------------------------
# Requisito de Recuperación
# ---------------------------------------------------------------------------

class RequisitoRecuperacionSerializer(serializers.ModelSerializer):
    profesor_nombre = serializers.SerializerMethodField()
    profesor_correo = serializers.SerializerMethodField()
    uea_nombre = serializers.CharField(source="uea.nombre", read_only=True)
    uea_clave = serializers.CharField(source="uea.clave", read_only=True)
    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)

    def get_profesor_nombre(self, obj):
        return _profesor_nombre(obj)

    def get_profesor_correo(self, obj):
        return _profesor_correo(obj)

    class Meta:
        model = RequisitoRecuperacion
        fields = [
            "id", "profesor", "profesor_nombre", "profesor_correo",
            "uea", "uea_nombre", "uea_clave",
            "periodo", "periodo_clave",
            "nombre_grupo", "id_grupo", "horario", "modalidad",
            # Contenido propio del Requisito de Recuperación
            "lugar", "duracion_aprox", "fecha_hora",
            "recursos_necesarios", "requisitos", "notas",
            "estado",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "profesor", "periodo", "created_at", "updated_at"]

    def validate(self, attrs):
        # Misma regla que CartaTematica: solo editable en BORRADOR.
        if self.instance and self.instance.estado != RequisitoRecuperacion.Estado.BORRADOR:
            raise serializers.ValidationError(
                "Solo se pueden editar documentos en BORRADOR. "
                "Despublica el requisito primero."
            )
        return attrs


# ---------------------------------------------------------------------------
# Vista pública (sin auth) — Solo lectura, datos no sensibles
# ---------------------------------------------------------------------------

class PublicDocumentoListSerializer(serializers.Serializer):
    """Serializer ligero para listar Cartas Temáticas y Requisitos de Recuperación
    en la vista pública. Solo expone datos seguros para mostrar en una tarjeta
    de resumen — el usuario abre el detalle completo en la vista respectiva.
    """

    id = serializers.IntegerField(read_only=True)
    profesor_nombre = serializers.SerializerMethodField()
    uea_clave = serializers.CharField(source="uea.clave", read_only=True)
    uea_nombre = serializers.CharField(source="uea.nombre", read_only=True)
    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)
    nombre_grupo = serializers.CharField(read_only=True)
    id_grupo = serializers.CharField(read_only=True)
    horario = serializers.CharField(read_only=True)
    modalidad = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def get_profesor_nombre(self, obj):
        return _profesor_nombre(obj)


class PublicCartaTematicaSerializer(serializers.ModelSerializer):
    """Versión pública de la Carta Temática.

    Solo expone datos del profesor y de la UEA visibles a cualquier persona,
    sin IDs internos de `usuario` ni metadatos administrativos. Si el
    profesor fue eliminado, se usan los snapshots para preservar el histórico.
    """

    tipo_documento = serializers.SerializerMethodField()
    profesor_nombre = serializers.SerializerMethodField()
    profesor_correo = serializers.SerializerMethodField()
    uea_clave = serializers.CharField(source="uea.clave", read_only=True)
    uea_nombre = serializers.CharField(source="uea.nombre", read_only=True)
    uea_liga = serializers.CharField(source="uea.liga", read_only=True)
    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)

    class Meta:
        model = CartaTematica
        fields = [
            "id", "tipo_documento",
            "estado", "created_at",
            "profesor_nombre", "profesor_correo",
            "uea_clave", "uea_nombre", "uea_liga",
            "periodo_clave",
            "nombre_grupo", "id_grupo", "horario", "modalidad",
            "descripcion_uea", "objetivo_general", "objetivos_particulares",
            "contenido_sintetico", "objetivos_aprendizaje", "requerimientos",
            "conocimientos_previos", "modalidad_evaluacion",
            "revisiones_asesorias", "bibliografia", "calendarizacion_actividades",
        ]
        read_only_fields = fields

    def get_tipo_documento(self, _obj):
        return "Carta Temática"

    def get_profesor_nombre(self, obj):
        return _profesor_nombre(obj)

    def get_profesor_correo(self, obj):
        return _profesor_correo(obj)


class PublicRequisitoSerializer(serializers.ModelSerializer):
    """Versión pública del Requisito de Recuperación.

    Se titula como "Evaluación de Recuperación" para la vista pública.
    Si el profesor fue eliminado, usa los snapshots para el histórico.
    """

    tipo_documento = serializers.SerializerMethodField()
    profesor_nombre = serializers.SerializerMethodField()
    profesor_correo = serializers.SerializerMethodField()
    uea_clave = serializers.CharField(source="uea.clave", read_only=True)
    uea_nombre = serializers.CharField(source="uea.nombre", read_only=True)
    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)

    class Meta:
        model = RequisitoRecuperacion
        fields = [
            "id", "tipo_documento",
            "estado", "created_at",
            "profesor_nombre", "profesor_correo",
            "uea_clave", "uea_nombre",
            "periodo_clave",
            "nombre_grupo", "id_grupo", "horario", "modalidad",
            "lugar", "duracion_aprox", "fecha_hora",
            "recursos_necesarios", "requisitos", "notas",
        ]
        read_only_fields = fields

    def get_tipo_documento(self, _obj):
        return "Evaluación de Recuperación"

    def get_profesor_nombre(self, obj):
        return _profesor_nombre(obj)

    def get_profesor_correo(self, obj):
        return _profesor_correo(obj)
