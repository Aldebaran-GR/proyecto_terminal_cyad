"""Serializers de documentos académicos.

Después del rediseño los documentos son planos (sin sub-modelos): solo campos
de texto libre. Esto simplifica drásticamente create/update.

Adicionalmente, se exponen dos serializers de **vista pública** que devuelven
solo los campos seguros (sin IDs internos del usuario) y un campo
`tipo_documento` constante para que la UI pública lo muestre como título.
"""

from rest_framework import serializers

from .models import CartaTematica, RequisitoRecuperacion


# ---------------------------------------------------------------------------
# Carta Temática
# ---------------------------------------------------------------------------

class CartaTematicaSerializer(serializers.ModelSerializer):
    """Serializer interno (profesor / admin) — incluye todos los campos."""

    profesor_nombre = serializers.CharField(
        source="profesor.nombre_completo", read_only=True
    )
    uea_nombre = serializers.CharField(source="uea.nombre", read_only=True)
    uea_clave = serializers.CharField(source="uea.clave", read_only=True)
    uea_liga = serializers.CharField(source="uea.liga", read_only=True)
    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)

    class Meta:
        model = CartaTematica
        fields = [
            "id", "profesor", "profesor_nombre",
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
    profesor_nombre = serializers.CharField(
        source="profesor.nombre_completo", read_only=True
    )
    uea_nombre = serializers.CharField(source="uea.nombre", read_only=True)
    uea_clave = serializers.CharField(source="uea.clave", read_only=True)
    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)

    class Meta:
        model = RequisitoRecuperacion
        fields = [
            "id", "profesor", "profesor_nombre",
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

class PublicCartaTematicaSerializer(serializers.ModelSerializer):
    """Versión pública de la Carta Temática.

    Solo expone datos del profesor y de la UEA visibles a cualquier persona,
    sin IDs internos de `usuario` ni metadatos administrativos.
    """

    tipo_documento = serializers.SerializerMethodField()
    profesor_nombre = serializers.CharField(
        source="profesor.nombre_completo", read_only=True
    )
    profesor_correo = serializers.CharField(
        source="profesor.correo_institucional", read_only=True
    )
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


class PublicRequisitoSerializer(serializers.ModelSerializer):
    """Versión pública del Requisito de Recuperación.

    Se titula como "Evaluación de Recuperación" para la vista pública.
    """

    tipo_documento = serializers.SerializerMethodField()
    profesor_nombre = serializers.CharField(
        source="profesor.nombre_completo", read_only=True
    )
    profesor_correo = serializers.CharField(
        source="profesor.correo_institucional", read_only=True
    )
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
