# Diagrama Entidad-Relación — Sistema Proyecto Terminal CyAD

- **Fecha de generación:** 2026-08-11
- **Alcance:** 18 tablas de dominio en 4 apps Django (`accounts`, `catalogos`, `documentos`, `autoevaluacion`).
- **Fuera de alcance:** tablas internas de Django (`auth_*`, `django_session`, `token_blacklist_*`).
- **Fuente:** modelos en `backend/{accounts,catalogos,documentos,autoevaluacion}/models.py`.

## Convenciones

- **PK / FK / UK** identifican clave primaria, foránea y unicidad simple.
- Tipo `datetime`, `date`, `decimal`, `text`, `json`, `email`, `url`, `int`, `bool`, `string` (todos son abstracciones de los tipos Django/PostgreSQL reales).
- Cardinalidad Mermaid:
  - `||--o{` — uno a muchos (FK obligatoria en el hijo).
  - `|o--o{` — cero-o-uno a muchos (FK nullable en el hijo).
  - `||--o|` — uno a uno (relación opcional del lado hijo).
  - `}o--o{` — muchos a muchos.
- La etiqueta de cada relación anota la política **on_delete** del FK (`PROTECT`, `SET_NULL`, `CASCADE`) y, cuando aporta, el `related_name`.
- Los campos heredados de mixins abstractos se replican en cada entidad concreta:
  - `TimeStampedModel` → `created_at`, `updated_at`.
  - `EstadoActivoModel` → `estado` (bool, borrado lógico).
- `DocumentoAcademicoBase` es abstracta y no se representa como entidad; sus campos aparecen en `CartaTematica` y `RequisitoRecuperacion`.

## Diagrama

```mermaid
erDiagram
    %% ────────────────────────────────────────────────────────────
    %% accounts
    %% ────────────────────────────────────────────────────────────
    Usuario {
        int id PK
        string password
        datetime last_login
        bool is_superuser
        email email UK
        string nombre
        string rol "ADMIN|PROFESOR"
        bool is_active
        bool is_staff
        datetime created_at
        datetime updated_at
    }

    Profesor {
        int id PK
        int usuario_id FK,UK
        string numero_economico UK "nullable"
        string nombre_completo
        email correo_institucional UK
        int departamento_id FK "nullable"
        bool estado
        datetime created_at
        datetime updated_at
    }

    %% ────────────────────────────────────────────────────────────
    %% catalogos
    %% ────────────────────────────────────────────────────────────
    Departamento {
        int id PK
        string clave UK
        string nombre
        bool estado
        datetime created_at
        datetime updated_at
    }

    Licenciatura {
        int id PK
        string clave UK
        string nombre
        int orden
        int departamento_id FK "nullable"
        bool estado
        datetime created_at
        datetime updated_at
    }

    Posgrado {
        int id PK
        string clave UK
        string nombre
        int orden
        int departamento_id FK "nullable"
        bool estado
        datetime created_at
        datetime updated_at
    }

    Area {
        int id PK
        string nombre
        string descripcion
        bool estado
        datetime created_at
        datetime updated_at
    }

    UEA {
        int id PK
        string clave
        string nombre
        int licenciatura_id FK "nullable, XOR posgrado"
        int posgrado_id FK "nullable, XOR licenciatura"
        int area_id FK "nullable"
        string trimestre
        string tipo "OBL|OPT|OTRO"
        int creditos "nullable"
        url liga
        bool estado
        datetime created_at
        datetime updated_at
    }

    Periodo {
        int id PK
        string clave UK
        date fecha_inicio
        date fecha_fin
        bool activo_cartas
        bool activo_requisitos
        bool activo_autoevaluacion
        bool activo "derivado, no editable"
        bool estado
        datetime created_at
        datetime updated_at
    }

    %% ────────────────────────────────────────────────────────────
    %% documentos
    %% ────────────────────────────────────────────────────────────
    CartaTematica {
        int id PK
        int profesor_id FK "nullable, snapshot en profesor_nombre/correo"
        string profesor_nombre
        email profesor_correo
        int uea_id FK
        int periodo_id FK
        string nombre_grupo
        string id_grupo
        string horario
        string modalidad "PRESENCIAL|REMOTO|MIXTO"
        string estado "BORRADOR|PUBLICADO"
        text descripcion_uea
        text objetivo_general
        text objetivos_particulares
        text contenido_sintetico
        text objetivos_aprendizaje
        text requerimientos
        text conocimientos_previos
        text modalidad_evaluacion
        text revisiones_asesorias
        text bibliografia
        text enlace
        text calendarizacion_actividades
        datetime created_at
        datetime updated_at
    }

    RequisitoRecuperacion {
        int id PK
        int profesor_id FK "nullable, snapshot en profesor_nombre/correo"
        string profesor_nombre
        email profesor_correo
        int uea_id FK
        int periodo_id FK
        string nombre_grupo
        string id_grupo
        string horario
        string modalidad "PRESENCIAL|REMOTO|MIXTO"
        string estado "BORRADOR|PUBLICADO"
        text lugar
        string duracion_aprox
        string fecha_hora
        text recursos_necesarios
        text requisitos
        text notas
        datetime created_at
        datetime updated_at
    }

    %% ────────────────────────────────────────────────────────────
    %% autoevaluacion
    %% ────────────────────────────────────────────────────────────
    Formulario {
        int id PK
        string titulo
        text descripcion
        int periodo_id FK
        string estado "BORRADOR|PUBLICADO|CERRADO"
        int version
        bool una_respuesta_por_profesor
        int created_by_id FK "nullable, Usuario"
        datetime published_at "nullable"
        datetime closed_at "nullable"
        datetime created_at
        datetime updated_at
    }

    Seccion {
        int id PK
        int formulario_id FK
        string titulo
        text descripcion
        int orden
        decimal peso "porcentaje 0-100"
    }

    Pregunta {
        int id PK
        int formulario_id FK
        int seccion_id FK "nullable"
        string tipo "TEXTO_CORTO|TEXTO_LARGO|OPCION_UNICA|CASILLAS|SI_NO|ESCALA_LINEAL|LISTA_DESPLEGABLE|CUADRICULA"
        text texto
        string ayuda
        bool obligatoria
        int orden
        json config "params por tipo"
    }

    OpcionPregunta {
        int id PK
        int pregunta_id FK
        string texto
        string valor
        decimal puntos
        int orden
    }

    FilaCuadricula {
        int id PK
        int pregunta_id FK
        string texto
        int orden
    }

    NivelDesempeno {
        int id PK
        int formulario_id FK
        string nombre
        decimal porcentaje_min
        decimal porcentaje_max
        text observacion
        string color "green|blue|yellow|red|gray"
        int orden
    }

    Respuesta {
        int id PK
        int formulario_id FK
        int profesor_id FK
        int version_formulario
        string estado "BORRADOR|ENVIADO"
        datetime enviado_at "nullable"
        decimal puntaje_obtenido "nullable"
        decimal puntaje_maximo "nullable"
        decimal porcentaje "nullable"
        int nivel_desempeno_id FK "nullable"
        datetime created_at
        datetime updated_at
    }

    RespuestaPregunta {
        int id PK
        int respuesta_id FK
        int pregunta_id FK
        text valor_texto
    }

    RespuestaCelda {
        int id PK
        int respuesta_pregunta_id FK
        int fila_id FK
        int opcion_id FK
    }

    RespuestaSeccion {
        int id PK
        int respuesta_id FK
        int seccion_id FK
        decimal peso "snapshot"
        decimal puntaje_obtenido
        decimal puntaje_maximo
        decimal porcentaje
    }

    %% ────────────────────────────────────────────────────────────
    %% Relaciones
    %% ────────────────────────────────────────────────────────────

    %% accounts
    Usuario ||--o| Profesor : "CASCADE / perfil_profesor"

    %% catalogos
    Departamento ||--o{ Licenciatura : "SET_NULL / licenciaturas"
    Departamento ||--o{ Posgrado     : "SET_NULL / posgrados"
    Departamento ||--o{ Profesor     : "SET_NULL / profesores"
    Licenciatura |o--o{ UEA          : "PROTECT / ueas"
    Posgrado     |o--o{ UEA          : "PROTECT / ueas"
    Area         |o--o{ UEA          : "PROTECT / ueas"

    %% documentos
    Profesor |o--o{ CartaTematica         : "SET_NULL / cartatematica_set"
    Profesor |o--o{ RequisitoRecuperacion : "SET_NULL / requisitorecuperacion_set"
    UEA      ||--o{ CartaTematica         : "PROTECT / cartatematica_set"
    UEA      ||--o{ RequisitoRecuperacion : "PROTECT / requisitorecuperacion_set"
    Periodo  ||--o{ CartaTematica         : "PROTECT / cartatematica_set"
    Periodo  ||--o{ RequisitoRecuperacion : "PROTECT / requisitorecuperacion_set"

    %% autoevaluacion — estructura
    Periodo    ||--o{ Formulario     : "PROTECT / formularios"
    Usuario    |o--o{ Formulario     : "SET_NULL / created_by"
    Formulario ||--o{ Seccion        : "CASCADE / secciones"
    Formulario ||--o{ Pregunta       : "CASCADE / preguntas"
    Formulario ||--o{ NivelDesempeno : "CASCADE / niveles"
    Seccion    |o--o{ Pregunta       : "SET_NULL / preguntas"
    Pregunta   ||--o{ OpcionPregunta : "CASCADE / opciones"
    Pregunta   ||--o{ FilaCuadricula : "CASCADE / filas"

    %% autoevaluacion — respuestas
    Formulario     ||--o{ Respuesta          : "PROTECT / respuestas"
    Profesor       ||--o{ Respuesta          : "PROTECT / respuestas_formulario"
    NivelDesempeno |o--o{ Respuesta          : "SET_NULL / respuestas"
    Respuesta      ||--o{ RespuestaPregunta  : "CASCADE / items"
    Respuesta      ||--o{ RespuestaSeccion   : "CASCADE / secciones_resultado"
    Pregunta       ||--o{ RespuestaPregunta  : "PROTECT / respuestas_recibidas"
    Seccion        ||--o{ RespuestaSeccion   : "PROTECT / resultados"
    RespuestaPregunta ||--o{ RespuestaCelda  : "CASCADE / celdas"
    FilaCuadricula    ||--o{ RespuestaCelda  : "PROTECT"
    OpcionPregunta    ||--o{ RespuestaCelda  : "PROTECT"

    %% M2M — Django genera tabla intermedia autoevaluacion_respuestapregunta_opciones_seleccionadas
    RespuestaPregunta }o--o{ OpcionPregunta : "M2M opciones_seleccionadas"
```

## Constraints compuestos

Restricciones que no se pueden expresar solo con `UK` en el diagrama:

| Modelo | Tipo | Definición | Motivo |
|---|---|---|---|
| `UEA` | CHECK | `uea_xor_licenciatura_posgrado`: exactamente uno entre `licenciatura` y `posgrado` es no nulo | Una UEA pertenece a una licenciatura **o** a un posgrado, nunca a ambos ni a ninguno |
| `UEA` | UniqueConstraint (parcial) | `uea_clave_unica_por_licenciatura`: `(clave, licenciatura)` cuando `licenciatura` no es nulo | Cada licenciatura no puede tener dos UEA con la misma clave |
| `UEA` | UniqueConstraint (parcial) | `uea_clave_unica_por_posgrado`: `(clave, posgrado)` cuando `posgrado` no es nulo | Análogo para posgrado |
| `Area` | unique_together | `(nombre, descripcion)` | Evita áreas duplicadas |
| `CartaTematica` | UniqueConstraint | `unique_carta_profesor_periodo_uea_grupo`: `(profesor, periodo, uea, id_grupo)` | Un profesor no puede tener dos cartas para el mismo grupo y periodo |
| `RequisitoRecuperacion` | UniqueConstraint | `unique_requisito_profesor_periodo_uea_grupo`: `(profesor, periodo, uea, id_grupo)` | Análogo para requisitos de recuperación |
| `Respuesta` | UniqueConstraint | `unique_respuesta_formulario_profesor_version`: `(formulario, profesor, version_formulario)` | Un profesor responde una sola vez por versión del formulario; al publicar una revisión se incrementa `version` y puede volver a responder |
| `RespuestaPregunta` | unique_together | `(respuesta, pregunta)` | Cada pregunta se contesta a lo más una vez por respuesta |
| `RespuestaCelda` | unique_together | `(respuesta_pregunta, fila)` | Cada fila de cuadrícula tiene una única opción seleccionada |
| `RespuestaSeccion` | unique_together | `(respuesta, seccion)` | Un snapshot por sección al enviar |
| `Periodo` | Regla en `save()` | Solo un `Periodo` puede tener `activo_cartas=True`, otro con `activo_requisitos=True`, otro con `activo_autoevaluacion=True`. El campo `activo` es OR derivado | Independiza el ciclo por recurso (Cartas del trimestre N+1, Requisitos/Autoeval del N) |

## Notas de comportamiento clave

- **Snapshot histórico de profesor** (documentos): `profesor_id` es `SET_NULL`; al eliminar al profesor, `profesor_nombre` y `profesor_correo` conservan quién era el autor. Por eso los documentos sobreviven al ciclo de vida del `Profesor`.
- **Versionado de formularios**: `Respuesta.version_formulario` congela la versión del `Formulario` respondida. Publicar una revisión (`publicar_revision`) incrementa `Formulario.version`; los profesores ven el formulario como pendiente porque su última respuesta apunta a una versión anterior. Las respuestas viejas se conservan como historial.
- **Snapshot de pesos** en `RespuestaSeccion.peso`: se copia desde `Seccion.peso` al enviar para que el desglose histórico permanezca estable aunque el admin ajuste pesos y republique.
- **Estados de documento** (`DocumentoAcademicoBase.Estado`): solo se puede editar/eliminar en `BORRADOR`; publicar bloquea la edición hasta despublicar.
