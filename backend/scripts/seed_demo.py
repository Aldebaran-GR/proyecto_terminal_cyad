"""Seed completo para demostración E2E.

Crea:
- Usuarios: 1 ADMIN + 2 PROFESORES (con su perfil)
- Catálogos: Departamentos, Licenciaturas (vinculadas a departamento), 4 UEAs
  de prueba y un Periodo 26-I activo
- Autoevaluación demo: 1 Formulario PUBLICADO con secciones, preguntas
  (todos los tipos), opciones con puntos y 3 niveles de desempeño

Uso (desde backend/):
    python scripts/seed_demo.py

Idempotente: puede correrse varias veces sin duplicar registros.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from accounts.models import Profesor, Usuario  # noqa: E402
from autoevaluacion.models import (  # noqa: E402
    Formulario,
    NivelDesempeno,
    OpcionPregunta,
    Pregunta,
    Seccion,
)
from catalogos.models import (  # noqa: E402
    UEA,
    Area,
    Departamento,
    Licenciatura,
    Periodo,
    Posgrado,
)


def banner(msg: str) -> None:
    print(f"\n=== {msg} ===")


# ─── 1. Usuarios ──────────────────────────────────────────────────────────────
banner("Usuarios")

USERS = [
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
        "nombre": "Mariana López Hdz.",
        "password": "Profesor1234!",
        "rol": Usuario.Rol.PROFESOR,
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "email": "profesor2@cyad.uam.mx",
        "nombre": "Javier Ortega Ríos",
        "password": "Profesor1234!",
        "rol": Usuario.Rol.PROFESOR,
        "is_staff": False,
        "is_superuser": False,
    },
]

usuarios_por_email: dict[str, Usuario] = {}
for data in USERS:
    password = data.pop("password")
    obj, created = Usuario.objects.get_or_create(
        email=data["email"], defaults=data,
    )
    if created:
        obj.set_password(password)
        obj.save()
        print(f"  [CREADO] {obj.email} ({obj.rol})")
    else:
        print(f"  [EXISTE] {obj.email} ({obj.rol})")
    usuarios_por_email[obj.email] = obj


# ─── 2. Catálogos (fixtures cubren depto/lic/periodos, refrescamos aquí) ─────
banner("Catálogos — Departamentos / Licenciaturas / Periodo activo")

DEPARTAMENTOS = [
    ("EDT", "Evaluación del Diseño en el Tiempo"),
    ("ICD", "Investigación y Conocimiento para el Diseño"),
    ("PTR", "Procesos y Técnicas de Realización"),
    ("MA",  "Medio Ambiente"),
]
for clave, nombre in DEPARTAMENTOS:
    obj, created = Departamento.objects.get_or_create(
        clave=clave, defaults={"nombre": nombre, "estado": True},
    )
    marker = "CREADO" if created else "EXISTE"
    print(f"  [{marker}] Depto {clave} — {nombre}")

# Orden y clave alineados al CSV institucional (licenciaturas.csv).
LICENCIATURAS = [
    (1, "DCG",  "Diseño de la Comunicación Gráfica",     "ICD"),
    (2, "ARQ",  "Arquitectura",                          "EDT"),
    (3, "DI",   "Diseño Industrial",                     "PTR"),
    (4, "DiPS", "Diseño de Proyectos Sustentables",      "MA"),
]
# Si quedó alguna fila legada con clave "DPS", la renombramos antes del upsert.
Licenciatura.objects.filter(clave="DPS").update(clave="DiPS")
for orden, clave, nombre, depto_clave in LICENCIATURAS:
    depto = Departamento.objects.filter(clave=depto_clave).first()
    obj, created = Licenciatura.objects.get_or_create(
        clave=clave,
        defaults={
            "nombre": nombre,
            "orden": orden,
            "departamento": depto,
            "estado": True,
        },
    )
    cambios = {}
    if obj.orden != orden:
        cambios["orden"] = orden
    if obj.departamento_id != (depto.id if depto else None):
        cambios["departamento"] = depto
    if cambios:
        for k, v in cambios.items():
            setattr(obj, k, v)
        obj.save(update_fields=list(cambios.keys()))
    marker = "CREADO" if created else "EXISTE"
    print(f"  [{marker}] Lic {clave} — {nombre}")

# Posgrado demo — usado para validar el XOR licenciatura/posgrado en UEA.
posgrado_demo, created = Posgrado.objects.get_or_create(
    clave="PDB",
    defaults={
        "nombre": "Posgrado en Diseño Bioclimático",
        "orden": 1,
        "estado": True,
    },
)
marker = "CREADO" if created else "EXISTE"
print(f"  [{marker}] Posgrado {posgrado_demo.clave} — {posgrado_demo.nombre}")

periodo, created = Periodo.objects.get_or_create(
    clave="26-I",
    defaults={
        "fecha_inicio": date(2026, 1, 12),
        "fecha_fin": date(2026, 4, 17),
        # Por defecto, el periodo demo está activo para los 3 recursos.
        # El admin puede luego repartir los flags entre periodos (ej. dejar
        # 26-P activo para Requisitos+AE y 26-O activo para Cartas).
        "activo_cartas": True,
        "activo_requisitos": True,
        "activo_autoevaluacion": True,
        "estado": True,
    },
)
if not (periodo.activo_cartas and periodo.activo_requisitos and periodo.activo_autoevaluacion):
    periodo.activo_cartas = True
    periodo.activo_requisitos = True
    periodo.activo_autoevaluacion = True
    periodo.save()
print(f"  [{'CREADO' if created else 'ACTIVO'}] Periodo {periodo.clave}")


# ─── 3. Áreas + UEAs demo ────────────────────────────────────────────────────
banner("Áreas demo")

AREAS_DEMO = [
    ("Licenciatura", "Licenciatura"),
    ("Optativas de Extensión Divisional", "Optativas Disciplinares"),
]
for nombre, descripcion in AREAS_DEMO:
    obj, created = Area.objects.get_or_create(
        nombre=nombre, descripcion=descripcion,
        defaults={"estado": True},
    )
    marker = "CREADO" if created else "EXISTE"
    print(f"  [{marker}] Área {nombre} — {descripcion}")

area_lic = Area.objects.get(nombre="Licenciatura", descripcion="Licenciatura")

banner("UEAs demo")

UEAS = [
    ("1100001", "Introducción al Diseño",            "ARQ",  "1", UEA.Tipo.OBLIGATORIA,  9),
    ("1403004", "Taller de Diseño Industrial I",     "DI",   "4", UEA.Tipo.OBLIGATORIA, 12),
    ("1200015", "Tipografía Aplicada",               "DCG",  "3", UEA.Tipo.OBLIGATORIA,  9),
    ("1500020", "Sustentabilidad y Proyecto",        "DiPS", "6", UEA.Tipo.OBLIGATORIA,  9),
]
for clave, nombre, lic_clave, trim, tipo, creditos in UEAS:
    lic = Licenciatura.objects.get(clave=lic_clave)
    obj, created = UEA.objects.get_or_create(
        clave=clave,
        defaults={
            "nombre": nombre,
            "licenciatura": lic,
            "area": area_lic,
            "trimestre": trim,
            "tipo": tipo,
            "creditos": creditos,
            "estado": True,
        },
    )
    marker = "CREADO" if created else "EXISTE"
    print(f"  [{marker}] UEA {clave} — {nombre}")

# UEA de posgrado demo — sin licenciatura, con posgrado (valida el XOR).
obj, created = UEA.objects.get_or_create(
    clave="9000001",
    defaults={
        "nombre": "Seminario de Diseño Bioclimático I",
        "posgrado": posgrado_demo,
        "area": area_lic,
        "trimestre": "1",
        "tipo": UEA.Tipo.OBLIGATORIA,
        "creditos": 9,
        "estado": True,
    },
)
marker = "CREADO" if created else "EXISTE"
print(f"  [{marker}] UEA {obj.clave} — {obj.nombre} (Posgrado {posgrado_demo.clave})")


# ─── 4. Perfiles de Profesor ─────────────────────────────────────────────────
banner("Perfiles de Profesor")

PROFESORES = [
    {
        "email": "profesor@cyad.uam.mx",
        "numero_economico": "30201",
        "nombre_completo": "Mariana López Hernández",
        "correo_institucional": "mlopez@azc.uam.mx",
        "departamento": "PTR",
    },
    {
        "email": "profesor2@cyad.uam.mx",
        "numero_economico": "30245",
        "nombre_economico_alt": None,
        "nombre_completo": "Javier Ortega Ríos",
        "correo_institucional": "jortega@azc.uam.mx",
        "departamento": "ICD",
    },
]
for p in PROFESORES:
    user = usuarios_por_email[p["email"]]
    depto = Departamento.objects.get(clave=p["departamento"])
    obj, created = Profesor.objects.get_or_create(
        usuario=user,
        defaults={
            "numero_economico": p["numero_economico"],
            "nombre_completo": p["nombre_completo"],
            "correo_institucional": p["correo_institucional"],
            "departamento": depto,
            "estado": True,
        },
    )
    marker = "CREADO" if created else "EXISTE"
    print(f"  [{marker}] Profesor {obj.nombre_completo}")


# ─── 5. Formulario de Autoevaluación demo ───────────────────────────────────
banner("Autoevaluación — Formulario demo")

admin_user = usuarios_por_email["admin@cyad.uam.mx"]

formulario, created = Formulario.objects.get_or_create(
    titulo="Autoevaluación Docente 26-I",
    periodo=periodo,
    defaults={
        "descripcion": "Formulario de autoevaluación del periodo 26-I para profesores CyAD.",
        "estado": Formulario.Estado.BORRADOR,
        "created_by": admin_user,
    },
)
if created:
    print(f"  [CREADO] Formulario {formulario.titulo}")
else:
    print(f"  [EXISTE] Formulario {formulario.titulo} (estado={formulario.estado})")

# Construir secciones + preguntas solo si está vacío (idempotencia)
if not formulario.preguntas.exists():
    sec1 = Seccion.objects.create(
        formulario=formulario, titulo="Planeación", orden=0,
        descripcion="Reflexión sobre la planeación del curso."
    )
    sec2 = Seccion.objects.create(
        formulario=formulario, titulo="Desempeño en aula", orden=1,
    )

    # P1 — OPCION_UNICA con opciones puntuables
    p1 = Pregunta.objects.create(
        formulario=formulario, seccion=sec1, orden=0,
        tipo=Pregunta.Tipo.OPCION_UNICA,
        texto="¿Con qué frecuencia entregaste la planeación del curso en tiempo?",
        obligatoria=True,
    )
    for orden, (texto, puntos) in enumerate([
        ("Siempre", "10"), ("Casi siempre", "7"), ("A veces", "4"), ("Nunca", "0"),
    ]):
        OpcionPregunta.objects.create(
            pregunta=p1, texto=texto, valor=texto, puntos=Decimal(puntos), orden=orden,
        )

    # P2 — CASILLAS (suma de seleccionadas)
    p2 = Pregunta.objects.create(
        formulario=formulario, seccion=sec1, orden=1,
        tipo=Pregunta.Tipo.CASILLAS,
        texto="¿Qué actividades de planeación realizaste? (marca todas las que apliquen)",
        obligatoria=True,
    )
    for orden, (texto, puntos) in enumerate([
        ("Carta temática actualizada", "5"),
        ("Calendarización de evaluaciones", "5"),
        ("Bibliografía revisada", "5"),
        ("Coordinación con academia", "5"),
    ]):
        OpcionPregunta.objects.create(
            pregunta=p2, texto=texto, valor=texto, puntos=Decimal(puntos), orden=orden,
        )

    # P3 — SI_NO
    p3 = Pregunta.objects.create(
        formulario=formulario, seccion=sec2, orden=2,
        tipo=Pregunta.Tipo.SI_NO,
        texto="¿Asististe puntualmente a todas las sesiones?",
        config={"puntos_si": 10, "puntos_no": 0},
        obligatoria=True,
    )

    # P4 — ESCALA_LINEAL 1..5, factor 2 => max 10
    p4 = Pregunta.objects.create(
        formulario=formulario, seccion=sec2, orden=3,
        tipo=Pregunta.Tipo.ESCALA_LINEAL,
        texto="Califica tu nivel de comunicación con el grupo:",
        config={"min": 1, "max": 5, "label_min": "Bajo", "label_max": "Alto", "puntos_factor": 2},
        obligatoria=True,
    )

    # P5 — LISTA_DESPLEGABLE
    p5 = Pregunta.objects.create(
        formulario=formulario, seccion=sec2, orden=4,
        tipo=Pregunta.Tipo.LISTA_DESPLEGABLE,
        texto="¿Cuántas tutorías individuales ofreciste por trimestre?",
        obligatoria=True,
    )
    for orden, (texto, puntos) in enumerate([
        ("Ninguna", "0"), ("1-2", "3"), ("3-5", "7"), ("Más de 5", "10"),
    ]):
        OpcionPregunta.objects.create(
            pregunta=p5, texto=texto, valor=texto, puntos=Decimal(puntos), orden=orden,
        )

    # P6 — TEXTO_LARGO (no puntuable)
    Pregunta.objects.create(
        formulario=formulario, seccion=sec2, orden=5,
        tipo=Pregunta.Tipo.TEXTO_LARGO,
        texto="Describe brevemente un reto pedagógico que enfrentaste este trimestre:",
        obligatoria=False,
    )

    # Niveles de desempeño (puntaje máximo posible: 10+20+10+10+10 = 60)
    NIVELES = [
        ("Sobresaliente", "85.00", "100.00",
         "Excelente desempeño. Continúa documentando buenas prácticas.", "green",  0),
        ("Satisfactorio", "60.00", "84.99",
         "Buen desempeño. Considera reforzar las áreas con menor puntaje.", "blue",   1),
        ("En desarrollo", "0.00",  "59.99",
         "Te recomendamos planear acciones de mejora con tu coordinación.", "yellow", 2),
    ]
    for nombre, pmin, pmax, obs, color, orden in NIVELES:
        NivelDesempeno.objects.create(
            formulario=formulario, nombre=nombre,
            porcentaje_min=Decimal(pmin), porcentaje_max=Decimal(pmax),
            observacion=obs, color=color, orden=orden,
        )
    print("  Preguntas, opciones y niveles creados.")
else:
    print("  Preguntas ya existen — se omite construcción.")

# Publicar si está en borrador
if formulario.estado == Formulario.Estado.BORRADOR:
    formulario.publicar()
    print(f"  Formulario publicado (v{formulario.version}).")


# ─── Cierre ──────────────────────────────────────────────────────────────────
banner("LISTO")
print(
    """
Credenciales de prueba:
  ADMIN     -> admin@cyad.uam.mx     / Admin1234!
  PROFESOR  -> profesor@cyad.uam.mx  / Profesor1234!
  PROFESOR  -> profesor2@cyad.uam.mx / Profesor1234!

Periodo activo: 26-I    Formulario publicado: "Autoevaluación Docente 26-I"
"""
)
