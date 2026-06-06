"""Serializers de documentos académicos con escritura anidada."""

from rest_framework import serializers

from .models import (
    Bibliografia,
    CartaTematica,
    CriterioEvaluacion,
    RequisitoItem,
    RequisitoRecuperacion,
    Subtema,
    Tema,
)


# ---------------------------------------------------------------------------
# Sub-modelos de Carta Temática
# ---------------------------------------------------------------------------

class SubtemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subtema
        fields = ["id", "orden", "descripcion"]


class TemaSerializer(serializers.ModelSerializer):
    subtemas = SubtemaSerializer(many=True, required=False)

    class Meta:
        model = Tema
        fields = ["id", "orden", "nombre", "objetivo", "num_sesiones", "subtemas"]


class BibliografiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bibliografia
        fields = ["id", "tipo", "referencia"]


class CriterioEvaluacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriterioEvaluacion
        fields = ["id", "descripcion", "ponderacion"]


# ---------------------------------------------------------------------------
# Carta Temática
# ---------------------------------------------------------------------------

class CartaTematicaSerializer(serializers.ModelSerializer):
    temas = TemaSerializer(many=True, required=False)
    bibliografias = BibliografiaSerializer(many=True, required=False)
    criterios = CriterioEvaluacionSerializer(many=True, required=False)

    profesor_nombre = serializers.CharField(
        source="profesor.nombre_completo", read_only=True
    )
    uea_nombre = serializers.CharField(source="uea.nombre", read_only=True)
    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)

    class Meta:
        model = CartaTematica
        fields = [
            "id", "profesor", "profesor_nombre",
            "uea", "uea_nombre", "periodo", "periodo_clave",
            "nombre_grupo", "id_grupo", "horario", "modalidad",
            "objetivo_general", "presentacion", "estado",
            "temas", "bibliografias", "criterios",
            "created_at", "updated_at",
        ]
        # `periodo` ahora es asignado automáticamente por el ViewSet en base
        # al periodo activo para Cartas Temáticas.
        read_only_fields = ["id", "profesor", "periodo", "created_at", "updated_at"]

    def validate(self, attrs):
        if self.instance and self.instance.estado == CartaTematica.Estado.ENVIADO:
            raise serializers.ValidationError(
                "No se puede modificar un documento en estado ENVIADO."
            )
        return attrs

    def _save_temas(self, carta, temas_data):
        carta.temas.all().delete()
        for tema_data in temas_data:
            subtemas_data = tema_data.pop("subtemas", [])
            tema = Tema.objects.create(carta=carta, **tema_data)
            for s in subtemas_data:
                Subtema.objects.create(tema=tema, **s)

    def _save_bibliografias(self, carta, bib_data):
        carta.bibliografias.all().delete()
        for b in bib_data:
            Bibliografia.objects.create(carta=carta, **b)

    def _save_criterios(self, carta, crit_data):
        carta.criterios.all().delete()
        for c in crit_data:
            CriterioEvaluacion.objects.create(carta=carta, **c)

    def create(self, validated_data):
        temas_data = validated_data.pop("temas", [])
        bib_data = validated_data.pop("bibliografias", [])
        crit_data = validated_data.pop("criterios", [])
        carta = CartaTematica.objects.create(**validated_data)
        self._save_temas(carta, temas_data)
        self._save_bibliografias(carta, bib_data)
        self._save_criterios(carta, crit_data)
        return carta

    def update(self, instance, validated_data):
        temas_data = validated_data.pop("temas", None)
        bib_data = validated_data.pop("bibliografias", None)
        crit_data = validated_data.pop("criterios", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if temas_data is not None:
            self._save_temas(instance, temas_data)
        if bib_data is not None:
            self._save_bibliografias(instance, bib_data)
        if crit_data is not None:
            self._save_criterios(instance, crit_data)
        return instance


# ---------------------------------------------------------------------------
# Requisito de Recuperación
# ---------------------------------------------------------------------------

class RequisitoItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequisitoItem
        fields = ["id", "orden", "descripcion"]


class RequisitoRecuperacionSerializer(serializers.ModelSerializer):
    items = RequisitoItemSerializer(many=True, required=False)
    profesor_nombre = serializers.CharField(
        source="profesor.nombre_completo", read_only=True
    )
    uea_nombre = serializers.CharField(source="uea.nombre", read_only=True)
    periodo_clave = serializers.CharField(source="periodo.clave", read_only=True)

    class Meta:
        model = RequisitoRecuperacion
        fields = [
            "id", "profesor", "profesor_nombre",
            "uea", "uea_nombre", "periodo", "periodo_clave",
            "nombre_grupo", "id_grupo", "horario", "modalidad",
            "espacio_modalidad", "indicaciones", "estado",
            "items", "created_at", "updated_at",
        ]
        # `periodo` ahora es asignado automáticamente por el ViewSet en base
        # al periodo activo para Requisitos de Recuperación.
        read_only_fields = ["id", "profesor", "periodo", "created_at", "updated_at"]

    def validate(self, attrs):
        if self.instance and self.instance.estado == RequisitoRecuperacion.Estado.ENVIADO:
            raise serializers.ValidationError(
                "No se puede modificar un documento en estado ENVIADO."
            )
        return attrs

    def _save_items(self, requisito, items_data):
        requisito.items.all().delete()
        for item in items_data:
            RequisitoItem.objects.create(requisito=requisito, **item)

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        requisito = RequisitoRecuperacion.objects.create(**validated_data)
        self._save_items(requisito, items_data)
        return requisito

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if items_data is not None:
            self._save_items(instance, items_data)
        return instance
