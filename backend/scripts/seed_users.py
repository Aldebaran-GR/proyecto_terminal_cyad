"""Crea usuarios de prueba: 1 ADMIN y 1 PROFESOR."""

import os
import sys
import django

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from accounts.models import Usuario

users = [
    {
        "email": "admin@cyad.uam.mx",
        "nombre": "Administrador CyAD",
        "password": "Admin1234!",
        "rol": Usuario.Rol.ADMIN,
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "email": "profesor@cyad.uam.mx",
        "nombre": "Profesor de Prueba",
        "password": "Profesor1234!",
        "rol": Usuario.Rol.PROFESOR,
        "is_staff": False,
        "is_superuser": False,
    },
]

for data in users:
    password = data.pop("password")
    obj, created = Usuario.objects.get_or_create(email=data["email"], defaults=data)
    if created:
        obj.set_password(password)
        obj.save()
        print(f"[CREADO]  {obj.email}  rol={obj.rol}")
    else:
        print(f"[EXISTE]  {obj.email}  rol={obj.rol}")

print("\nUsuarios de prueba listos.")
print("  ADMIN   -> admin@cyad.uam.mx   / Admin1234!")
print("  PROFESOR-> profesor@cyad.uam.mx / Profesor1234!")
