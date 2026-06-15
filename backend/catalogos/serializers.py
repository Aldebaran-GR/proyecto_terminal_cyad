"""Serializers de catálogos institucionales."""

from rest_framework import serializers

from .models import Area, Departamento, Licenciatura, Periodo, Posgrado, UEA


class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ["id", "clave", "nombre", "estado", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class LicenciaturaSerializer(serializers.ModelSerializer):
    departamento_nombre = serializers.CharField(
        source="departamento.nombre", read_only=True, default=None
    )

    class Meta:
        model = Licenciatura
        fields = [
            "id", "clave", "nombre", "orden", "departamento", "departamento_nombre",
            "estado", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PosgradoSerializer(serializers.ModelSerializer):
    departamento_nombre = serializers.CharField(
        source="departamento.nombre", read_only=True, default=None
    )

    class Meta:
        model = Posgrado
        fields = [
            "id", "clave", "nombre", "orden", "departamento", "departamento_nombre",
            "estado", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = [
            "id", "nombre", "descripcion", "estado",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UEASerializer(serializers.ModelSerializer):
    licenciatura_nombre = serializers.CharField(
        source="licenciatura.nombre", read_only=True, default=None
    )
    posgrado_nombre = serializers.CharField(
        source="posgrado.nombre", read_only=True, default=None
    )
    area_nombre = serializers.CharField(
        source="area.nombre", read_only=True, default=None
    )
    area_descripcion = serializers.CharField(
        source="area.descripcion", read_only=True, default=None
    )

    class Meta:
        model = UEA
        fields = [
            "id", "clave", "nombre",
            "licenciatura", "licenciatura_nombre",
            "posgrado", "posgrado_nombre",
            "area", "area_nombre", "area_descripcion",
            "trimestre", "tipo", "creditos", "liga", "estado",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        licenciatura = attrs.get("licenciatura", getattr(self.instance, "licenciatura", None))
        posgrado = attrs.get("posgrado", getattr(self.instance, "posgrado", None))
        if bool(licenciatura) == bool(posgrado):
            raise serializers.ValidationError(
                "Una UEA debe pertenecer a una Licenciatura o a un Posgrado (no ambos ni ninguno)."
            )
        return attrs


class PeriodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Periodo
        fields = [
            "id", "clave", "fecha_inicio", "fecha_fin",
            "activo_cartas", "activo_requisitos", "activo_autoevaluacion",
            "activo", "estado",
            "created_at", "updated_at",
        ]
        # `activo` ahora es derivado (OR de los tres flags por recurso);
        # nunca debería enviarse desde el cliente.
        read_only_fields = ["id", "activo", "created_at", "updated_at"]

    def validate(self, attrs):
        if attrs.get("fecha_inicio") and attrs.get("fecha_fin"):
            if attrs["fecha_inicio"] >= attrs["fecha_fin"]:
                raise serializers.ValidationError(
                    {"fecha_fin": "La fecha de fin debe ser posterior a la de inicio."}
                )
        return attrs
