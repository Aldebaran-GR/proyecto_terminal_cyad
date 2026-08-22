# Proyecto Terminal CyAD — UAM Azcapotzalco

Sistema web para que los profesores de la **División de Ciencias y Artes para el Diseño (CyAD)**, UAM Azcapotzalco, gestionen sus **Cartas Temáticas**, sus **Requisitos de Recuperación** y respondan **formularios de Autoevaluación** estilo Google Forms creados por el administrador.

- **Backend:** Django 5 + Django REST Framework + PostgreSQL + JWT
- **Frontend:** React 19 + Vite + Tailwind CSS v4 + TanStack Query + React Hook Form + Zod

---

## Tabla de contenido

1. [Arquitectura](#1-arquitectura)
2. [Requisitos](#2-requisitos)
3. [Configuración rápida](#3-configuración-rápida)
4. [Datos de prueba](#4-datos-de-prueba)
5. [Ejecución](#5-ejecución)
6. [Pruebas](#6-pruebas)
7. [Endpoints principales](#7-endpoints-principales)
8. [Estructura del repositorio](#8-estructura-del-repositorio)
9. [Hitos del desarrollo](#9-hitos-del-desarrollo)

---

## 1. Arquitectura

```
┌─────────────────────────┐         ┌─────────────────────────┐
│  Frontend  (Vite:5173)  │ ──HTTP─►│  Backend  (Django:8000) │
│  React + Tailwind +     │ ◄─JSON──│  DRF + JWT + ORM        │
│  TanStack Query         │         └────────────┬────────────┘
└─────────────────────────┘                      │
                                                 ▼
                                       ┌──────────────────┐
                                       │   PostgreSQL     │
                                       │ proyecto_terminal│
                                       │      _cyad       │
                                       └──────────────────┘
```

**Apps del backend** — `core`, `accounts`, `catalogos`, `documentos`, `autoevaluacion`, `reportes`.

**Modelo de dominio (resumen):**
- `Usuario(email, rol ∈ {ADMIN, PROFESOR})` 1—1 `Profesor`
- `Departamento` 1—* `Licenciatura` 1—* `UEA`
- `Profesor` 1—* `CartaTematica / RequisitoRecuperacion` *—1 `UEA / Periodo`
- `Formulario(version)` 1—* `Seccion` 1—* `Pregunta` 1—* `OpcionPregunta(puntos)`
- `Formulario` 1—* `NivelDesempeno(rango%)` y 1—* `Respuesta(puntaje, %, nivel)`
- Unicidad `Respuesta(formulario, profesor, version_formulario)` → permite re-responder cuando el admin publica una nueva revisión.

---

## 2. Requisitos

- **Python 3.11+**
- **Node.js 20+** y **npm 10+**
- **PostgreSQL 14+** corriendo localmente (o accesible por red)

---

## 3. Configuración rápida

### 3.1 Clonar y preparar variables

```bash
git clone <repo> proyecto_terminal_cyad
cd proyecto_terminal_cyad
cd backend
cp .env.example .env         # editar credenciales de PostgreSQL si es necesario
cd ..
```

### 3.2 Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cd ..
```

**Camino corto (Windows PowerShell)** — crea la BD, aplica migraciones y siembra los datos de demo en un solo comando:

```powershell
.\scripts\bootstrap.ps1
```

**Camino manual** — equivalente paso a paso (Windows/Linux/macOS):

```bash
cd backend
python scripts/create_db.py
python manage.py migrate
python scripts/seed_demo.py    # o loaddata + seed_users.py, ver §4
```

### 3.3 Frontend

```bash
cd ../frontend
npm install
# Si necesitas apuntar a un backend remoto:
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env.local
```

---

## 4. Datos de prueba

Carga **todo el dataset demo** (usuarios + catálogos enriquecidos + UEAs + formulario de autoevaluación publicado):

```bash
cd backend
python scripts/seed_demo.py
```

Credenciales generadas (idempotentes — pueden recargarse sin duplicar):

| Rol      | Email                    | Contraseña      |
|----------|--------------------------|-----------------|
| ADMIN    | `admin@cyad.uam.mx`      | `Admin1234!`    |
| PROFESOR | `profesor@cyad.uam.mx`   | `Profesor1234!` |
| PROFESOR | `profesor2@cyad.uam.mx`  | `Profesor1234!` |

Además crea: 4 departamentos · 4 licenciaturas (con depto) · periodo **26-I** activo · 4 UEAs de muestra · perfil de profesor con número económico y depto · formulario *Autoevaluación Docente 26-I* publicado con secciones, preguntas de todos los tipos, opciones con puntos y 3 niveles de desempeño.

---

## 5. Ejecución

En **dos terminales** distintas:

```bash
# Terminal 1 — backend
cd backend
.venv\Scripts\activate   # o source .venv/bin/activate
python manage.py runserver
# → http://localhost:8000
# → docs OpenAPI en http://localhost:8000/api/docs/
```

```bash
# Terminal 2 — frontend
cd frontend
npm run dev
# → http://localhost:5173
```

**Smoke test E2E** (con backend levantado y seed cargado):

```bash
cd backend
python scripts/smoke_test.py
```

Verifica: salud, login admin/profesor, `/auth/me`, catálogos, formularios disponibles, creación de respuesta, creación de carta temática y reportes.

---

## 6. Pruebas

### Backend (pytest + DRF)

```bash
cd backend
pytest
```

Cubre: auth/JWT, permisos por rol, CRUD de catálogos e importación CSV de UEA, CRUD de documentos con regla de propiedad y bloqueo de edición ajena, builder de autoevaluación, **cálculo de puntaje y versionado**, reportes (dashboard, cumplimiento, resumen AE).

### Frontend (build de producción)

```bash
cd frontend
npm run build
```

Verifica que el bundle compile sin errores. Para pruebas de UI puede usarse `vitest` (configurable en `vite.config.js`).

---

## 7. Endpoints principales

Todos bajo `/api/v1/`. JWT en `Authorization: Bearer <access>`.

| Método   | URL                                              | Rol         |
|----------|--------------------------------------------------|-------------|
| POST     | `/auth/login/` · `/auth/refresh/`                | público     |
| GET      | `/auth/me/`                                      | autenticado |
| CRUD     | `/departamentos/` · `/licenciaturas/` · `/uea/` · `/periodos/` | ADMIN (escritura), autenticados (lectura) |
| POST     | `/uea/import-csv/`                               | ADMIN       |
| CRUD     | `/profesores/` · `/usuarios/`                    | ADMIN       |
| CRUD     | `/cartas-tematicas/` · `/requisitos-recuperacion/` | PROFESOR (propios) · ADMIN (lectura) |
| CRUD     | `/formularios/` · `/secciones/` · `/preguntas/` · `/niveles-desempeno/` | ADMIN |
| POST     | `/formularios/{id}/publicar/` · `/cerrar/` · `/publicar_revision/` | ADMIN |
| GET      | `/formularios/{id}/estadisticas/`                | ADMIN       |
| GET      | `/formularios-disponibles/`                      | PROFESOR    |
| POST/PUT | `/respuestas/` · `/respuestas/{id}/enviar/`      | PROFESOR    |
| GET      | `/reportes/dashboard/` · `/reportes/cumplimiento-licenciatura/` · `/reportes/autoevaluacion/` | ADMIN |

Documentación viva (Swagger UI): **http://localhost:8000/api/docs/**

---

## 8. Estructura del repositorio

```
proyecto_terminal_cyad/
├── .env.example
├── README.md
├── backend/
│   ├── config/              # settings, urls, wsgi
│   ├── core/                # mixins (TimeStamped, EstadoActivo)
│   ├── accounts/            # Usuario, Profesor, JWT, /me
│   ├── catalogos/           # Departamento, Licenciatura, UEA, Periodo
│   │   └── fixtures/        # depto, licenciatura, periodos, UEA.csv
│   ├── documentos/          # CartaTematica, RequisitoRecuperacion
│   ├── autoevaluacion/      # Formulario, Seccion, Pregunta, Opcion, Nivel, Respuesta
│   ├── reportes/            # vistas de agregación (sin modelos)
│   ├── scripts/
│   │   ├── create_db.py     # crea la BD en PostgreSQL si no existe
│   │   ├── seed_users.py    # usuarios mínimos (admin + profesor)
│   │   ├── seed_demo.py     # seed completo para demo / E2E
│   │   └── smoke_test.py    # E2E vía API HTTP
│   ├── tests/               # pytest (auth, catálogos, documentos, AE, reportes)
│   ├── manage.py
│   ├── pytest.ini
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/             # clientes axios (auth, catalogos, documentos, AE, reportes)
    │   ├── auth/            # AuthContext, ProtectedRoute, RoleRoute
    │   ├── components/ui/   # Button, Table, Modal, FormField, Badge, Loading, Alert
    │   ├── layouts/         # AdminLayout, ProfesorLayout
    │   ├── pages/
    │   │   ├── admin/       # dashboard, catálogos, profesores, documentos, AE, reportes
    │   │   └── profesor/    # dashboard, cartas, requisitos, autoevaluación
    │   ├── App.jsx          # rutas + guards por rol
    │   └── main.jsx
    ├── package.json
    └── vite.config.js
```

---

## 9. Hitos del desarrollo

| Hito | Entregable | Estado |
|------|-----------|--------|
| M0 | Scaffold + custom User + conexión PostgreSQL                   | ✅ |
| M1 | Auth & roles (JWT, /me, permisos)                              | ✅ |
| M2 | Catálogos + seed + import CSV de UEA                            | ✅ |
| M3 | Documentos: Carta Temática + Requisitos                         | ✅ |
| M4 | Autoevaluación: builder + respuestas + **puntaje + versionado** | ✅ |
| M5 | Reportes / Dashboard                                            | ✅ |
| M6 | Frontend base (auth + routing + layouts)                        | ✅ |
| M7 | Frontend profesor                                               | ✅ |
| M8 | Frontend admin                                                  | ✅ |
| M9 | Integración, seed E2E, smoke test, documentación                | ✅ |

---

## Flujo de demostración recomendado

1. **ADMIN** entra en `http://localhost:5173/login`, redirige a `/admin`.
2. Revisa **Catálogos → UEA** y **Profesores**; abre **Documentos → Cartas** (vista global vacía aún).
3. Entra a **Autoevaluación**, abre *Autoevaluación Docente 26-I* → pestaña **Niveles** muestra los 3 rangos; pestaña **Estadísticas** está vacía.
4. **PROFESOR** entra en otro navegador (`profesor@cyad.uam.mx / Profesor1234!`), redirige a `/profesor`.
5. **Cartas Temáticas → Nueva** → selecciona UEA, grupo, horario, temas/bibliografía/criterios (la ponderación debe sumar 100%). Guarda como BORRADOR.
6. **Autoevaluación** → contesta el formulario publicado y envía. Aparece el **nivel de desempeño** correspondiente al porcentaje calculado.
7. **ADMIN** vuelve a **Autoevaluación → Estadísticas**: ve la respuesta contabilizada con porcentaje promedio y distribución por nivel.
8. **ADMIN** abre **Reportes** → tarjetas de profesores activos / cartas / requisitos y tabla de cumplimiento por licenciatura.
9. Para probar **versionado**: ADMIN cierra el formulario, lo abre y pulsa **Nueva revisión**. El profesor vuelve a tener el formulario disponible (v2) sin perder su respuesta v1.

---

## Notas técnicas

- `Usuario.USERNAME_FIELD = "email"`, definido **antes** de la primera migración (custom User irreversible).
- `EstadoActivoModel.estado` (BooleanField) reemplaza a `is_active` en `Profesor / Departamento / Licenciatura / UEA`. No confundir con `Usuario.is_active`.
- Solo un `Periodo` con `activo=True` (validado en `Periodo.save()`).
- `Pregunta.TIPOS_NO_PUNTABLES = {TEXTO_CORTO, TEXTO_LARGO}` — no contribuyen al puntaje.
- Configs por tipo de pregunta:
  - `ESCALA_LINEAL` → `{min, max, label_min, label_max, puntos_factor}` → `score = valor × puntos_factor`
  - `SI_NO` → `{puntos_si, puntos_no}` (defaults 1, 0)
- `Respuesta.version_formulario` se fija al crear con la versión actual del formulario; el constraint único permite múltiples respuestas del mismo profesor cuando la versión cambia.
