"""Serializers para autenticación y perfiles."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Profesor, Usuario


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Agrega datos del usuario al payload del token de login.

    Distingue entre **credenciales incorrectas** y **cuenta desactivada**
    para que el frontend pueda mostrar el mensaje adecuado. Django por
    defecto rechaza igual ambos casos (authenticate() devuelve None tanto
    si la contraseña es mala como si is_active=False), así que aquí
    verificamos manualmente la combinación email+password antes de delegar
    en el flujo estándar.
    """

    def validate(self, attrs):
        email = (attrs.get(self.username_field) or "").strip().lower()
        password = attrs.get("password") or ""

        # Intentamos identificar al usuario por email para distinguir los
        # dos motivos de fallo (cuenta desactivada vs contraseña incorrecta).
        usuario = Usuario.objects.filter(email__iexact=email).first()
        if usuario and usuario.check_password(password) and not usuario.is_active:
            # Credenciales correctas pero cuenta desactivada → mensaje claro.
            raise AuthenticationFailed(
                {
                    "code": "account_disabled",
                    "detail": (
                        "Tu cuenta se encuentra desactivada. "
                        "Contacta al administrador para reactivarla."
                    ),
                },
                code="account_disabled",
            )

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
        # Incluye `id` para que el cliente pueda usarlo en llamadas
        # subsecuentes (ej. crear el Profesor vinculado).
        fields = ["id", "email", "nombre", "rol", "password"]
        read_only_fields = ["id"]

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
    departamento_nombre = serializers.CharField(
        source="departamento.nombre", read_only=True, default=None,
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
            "departamento",         # FK (escritura + lectura del ID)
            "departamento_nombre",  # lectura conveniente para la lista
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
