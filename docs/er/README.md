# Diagrama Entidad-Relación

Documentación del modelo de datos del sistema. La fuente autoritativa es [`er.md`](er.md), que contiene un bloque Mermaid `erDiagram` con las 18 tablas de dominio, atributos, cardinalidades y políticas `on_delete`.

## Visualización

- **En GitHub / GitLab / VS Code**: `er.md` se renderiza inline automáticamente al abrirlo.
- **En el navegador**: pegar el bloque ` ```mermaid ... ``` ` en <https://mermaid.live>.
- **En VS Code**: instalar la extensión *Markdown Preview Mermaid Support* y usar la vista previa (Ctrl+Shift+V).

## Exportar a SVG / PNG (para embeber en el reporte LaTeX)

Con Node ≥18 disponible:

```bash
npx --yes @mermaid-js/mermaid-cli -i docs/er/er.md -o docs/er/er.svg
npx --yes @mermaid-js/mermaid-cli -i docs/er/er.md -o docs/er/er.png -w 2400
```

Para embeber en el reporte:

```latex
\includegraphics[width=\linewidth]{Imagenes/er.pdf}
```

(Convertir SVG→PDF con `rsvg-convert -f pdf docs/er/er.svg -o docs/reporte/Imagenes/er.pdf`, o usar el PNG directamente.)

## Cómo mantener el diagrama sincronizado con el código

Cuando cambien los modelos de `backend/{accounts,catalogos,documentos,autoevaluacion}/models.py`:

1. Actualizar la entidad afectada en `er.md` (atributos, PK/FK, tipo).
2. Si cambian relaciones (`ForeignKey`, `OneToOneField`, `ManyToManyField`), actualizar el bloque de relaciones al final del `erDiagram`, respetando la cardinalidad Mermaid:
   - FK `null=False` → `Padre ||--o{ Hijo`.
   - FK `null=True`  → `Padre |o--o{ Hijo`.
   - OneToOne `null=True` → `A ||--o| B`.
   - M2M → `A }o--o{ B`.
3. Anotar la política `on_delete` en la etiqueta (`PROTECT`, `SET_NULL`, `CASCADE`).
4. Si aparece o cambia un `UniqueConstraint` / `CheckConstraint` compuesto, actualizar la tabla **Constraints compuestos** de `er.md`.
5. Revisar la sintaxis pegando el bloque en <https://mermaid.live> antes de commitear.

## Relación con `docs/reporte/Imagenes/er.tex`

El archivo `er.tex` (TikZ) del reporte de tesis es una **vista resumida** — solo entidades y relaciones, sin atributos. Se mantiene manualmente y **no está sincronizado automáticamente** con este diagrama. Actualmente le faltan 3 entidades de `autoevaluacion` (`FilaCuadricula`, `RespuestaCelda`, `RespuestaSeccion`); considerar añadirlas la próxima vez que se recompile el reporte.

## Alcance

Se incluyen solo tablas del dominio del proyecto (18). Se omiten deliberadamente:

- Tablas internas de Django (`auth_user`, `auth_group`, `auth_permission`, `django_session`, `django_content_type`, `django_migrations`).
- Tablas de `rest_framework_simplejwt` (`token_blacklist_outstandingtoken`, `token_blacklist_blacklistedtoken`).
- La tabla intermedia M2M `autoevaluacion_respuestapregunta_opciones_seleccionadas` se representa como relación `}o--o{`, no como entidad separada.
