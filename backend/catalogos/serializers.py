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
    # Declarados explícitamente (en vez de dejar que ModelSerializer los
    # autogenere) porque las UniqueConstraint condicionales sobre
    # (clave, licenciatura) y (clave, posgrado) hacen que DRF fuerce
    # required=True en ambos campos por defecto — rompiendo el patrón XOR
    # donde solo uno de los dos se envía. La validación de unicidad real
    # ya la hace UEASerializer.validate().
    licenciatura = serializers.PrimaryKeyRelatedField(
        queryset=Licenciatura.objects.all(), required=False, allow_null=True
    )
    posgrado = serializers.PrimaryKeyRelatedField(
        queryset=Posgrado.objects.all(), required=False, allow_null=True
    )
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
        # DRF autogenera un UniqueTogetherValidator a partir de las
        # UniqueConstraint (clave, licenciatura) y (clave, posgrado) del
        # modelo, el cual exige que AMBOS campos estén presentes en el
        # payload (independientemente de required=False), rompiendo el
        # patrón XOR. Se desactiva porque validate() ya implementa el
        # chequeo real (case-insensitive, por rama del programa).
        validators = []

    def validate(self, attrs):
        licenciatura = attrs.get("licenciatura", getattr(self.instance, "licenciatura", None))
        posgrado = attrs.get("posgrado", getattr(self.instance, "posgrado", None))
        if bool(licenciatura) == bool(posgrado):
            raise serializers.ValidationError(
                "Una UEA debe pertenecer a una Licenciatura o a un Posgrado (no ambos ni ninguno)."
            )

        clave = attrs.get("clave", getattr(self.instance, "clave", None))
        if clave:
            qs = UEA.objects.filter(clave__iexact=clave.strip())
            qs = qs.filter(licenciatura=licenciatura) if licenciatura else qs.filter(posgrado=posgrado)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"clave": "Ya existe una UEA con esta clave en el programa seleccionado."}
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
        # `activo` es derivado (OR de los tres flags por recurso);
        # nunca debería enviarse desde el cliente.
        read_only_fields = ["id", "activo", "created_at", "updated_at"]

    def validate(self, attrs):
        if attrs.get("fecha_inicio") and attrs.get("fecha_fin"):
            if attrs["fecha_inicio"] >= attrs["fecha_fin"]:
                raise serializers.ValidationError(
                    {"fecha_fin": "La fecha de fin debe ser posterior a la de inicio."}
                )
        return attrs
