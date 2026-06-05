"""Serializers para autenticación y perfiles."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Profesor, Usuario


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Agrega datos del usuario al payload del token de login."""

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data["user"] = {
            "id": user.id,
            "email": user.email,
            "nombre": user.nombre,
            "rol": user.rol,
        }
        return data


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "email", "nombre", "rol", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Usuario
        fields = ["email", "nombre", "rol", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ProfesorSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(rol=Usuario.Rol.PROFESOR),
        source="usuario",
        write_only=True,
    )
    class Meta:
        model = Profesor
        fields = [
            "id",
            "usuario",
            "usuario_id",
            "numero_economico",
            "nombre_completo",
            "correo_institucional",
            "estado",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MeSerializer(serializers.ModelSerializer):
    """Datos del usuario autenticado, con perfil de profesor si aplica."""

    perfil_profesor = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ["id", "email", "nombre", "rol", "is_active", "perfil_profesor"]

    def get_perfil_profesor(self, obj):
        try:
            p = obj.perfil_profesor
            return {
                "id": p.id,
                "nombre_completo": p.nombre_completo,
                "correo_institucional": p.correo_institucional,
                "numero_economico": p.numero_economico,
                "estado": p.estado,
            }
        except Profesor.DoesNotExist:
            return None
