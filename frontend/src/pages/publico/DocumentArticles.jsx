/**
 * Componentes de artículo reutilizables para mostrar Cartas Temáticas y
 * Requisitos de Recuperación.
 *
 * Los usan tanto las páginas públicas (sin login) como las páginas de "Vista
 * previa" del profesor — la idea es que el profesor pueda ver exactamente
 * cómo lucirá el documento ante el público antes de publicarlo.
 */
import { PublicField } from './PublicDocumentLayout'

const URL_RE = /^https?:\/\/\S+$/i

function EnlaceField({ value }) {
  if (!value?.trim()) return null
  const lines = value.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  return (
    <div className="border-b border-slate-100 py-3 last:border-0">
      <p className="text-xs uppercase tracking-wider text-slate-500 mb-1">
        Enlace (clases en línea / asesorías)
      </p>
      <ul className="space-y-1 text-sm text-slate-800">
        {lines.map((line, i) =>
          URL_RE.test(line) ? (
            <li key={i}>
              <a
                href={line}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-600 hover:underline break-all"
              >
                {line}
              </a>
            </li>
          ) : (
            <li key={i} className="whitespace-pre-wrap">{line}</li>
          )
        )}
      </ul>
    </div>
  )
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('es-MX', {
      day: '2-digit', month: 'long', year: 'numeric',
    })
  } catch { return iso }
}


/* ─── Carta Temática ─────────────────────────────────────────────────────── */
export function CartaTematicaArticle({ carta, tituloOverride }) {
  return (
    <article className="rounded-xl bg-white border border-slate-200 p-8 print:border-0 print:p-0 space-y-8">
      <header className="border-b border-slate-200 pb-6">
        <p className="text-xs uppercase tracking-widest text-indigo-600 font-semibold">
          {tituloOverride ?? carta.tipo_documento ?? 'Carta Temática'}
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">
          {carta.uea_nombre}
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          <span className="font-mono">{carta.uea_clave}</span>
          {carta.uea_liga && (
            <>
              {' · '}
              <a
                href={carta.uea_liga}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-600 hover:underline"
              >
                Página oficial de la UEA ↗
              </a>
            </>
          )}
        </p>
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Profesor</p>
            <p className="text-slate-800">{carta.profesor_nombre}</p>
            <p className="text-slate-500 text-xs">
              {carta.profesor_correo ?? carta.correo_institucional}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Periodo · Grupo</p>
            <p className="text-slate-800">{carta.periodo_clave} · {carta.nombre_grupo}</p>
            <p className="text-slate-500 text-xs">
              ID grupo: {carta.id_grupo} · {carta.horario}
              {carta.modalidad && ` · ${carta.modalidad}`}
            </p>
          </div>
          <div className="col-span-2 text-xs text-slate-400">
            Creado: {formatDate(carta.created_at)}
          </div>
        </div>
      </header>

      <section className="space-y-1">
        <PublicField label="Descripción de la UEA"           value={carta.descripcion_uea} multiline />
        <PublicField label="Objetivo general"                value={carta.objetivo_general} multiline />
        <PublicField label="Objetivos particulares"          value={carta.objetivos_particulares} multiline />
        <PublicField label="Contenido sintético"             value={carta.contenido_sintetico} multiline />
        <PublicField label="Objetivos de aprendizaje"        value={carta.objetivos_aprendizaje} multiline />
        <PublicField label="Requerimientos"                  value={carta.requerimientos} multiline />
        <PublicField label="Conocimientos previos"           value={carta.conocimientos_previos} multiline />
        <PublicField label="Modalidad de evaluación"         value={carta.modalidad_evaluacion} multiline />
        <PublicField label="Revisiones / Asesorías"          value={carta.revisiones_asesorias} multiline />
        <PublicField label="Bibliografía"                    value={carta.bibliografia} multiline />
        <EnlaceField value={carta.enlace} />
        <PublicField label="Calendarización de actividades"  value={carta.calendarizacion_actividades} multiline />
      </section>
    </article>
  )
}


/* ─── Requisito de Recuperación ──────────────────────────────────────────── */
export function RequisitoArticle({ doc, tituloOverride }) {
  return (
    <article className="rounded-xl bg-white border border-slate-200 p-8 print:border-0 print:p-0 space-y-8">
      <header className="border-b border-slate-200 pb-6">
        <p className="text-xs uppercase tracking-widest text-indigo-600 font-semibold">
          {tituloOverride ?? doc.tipo_documento ?? 'Evaluación de Recuperación'}
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">{doc.uea_nombre}</h1>
        <p className="text-sm text-slate-500 mt-1">
          <span className="font-mono">{doc.uea_clave}</span>
        </p>
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Profesor</p>
            <p className="text-slate-800">{doc.profesor_nombre}</p>
            <p className="text-slate-500 text-xs">
              {doc.profesor_correo ?? doc.correo_institucional}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Periodo · Grupo</p>
            <p className="text-slate-800">{doc.periodo_clave} · {doc.nombre_grupo}</p>
            <p className="text-slate-500 text-xs">
              ID grupo: {doc.id_grupo} · {doc.horario}
              {doc.modalidad && ` · ${doc.modalidad}`}
            </p>
          </div>
          <div className="col-span-2 text-xs text-slate-400">
            Creado: {formatDate(doc.created_at)}
          </div>
        </div>
      </header>

      <section className="space-y-1">
        <PublicField label="Lugar"               value={doc.lugar}               multiline />
        <PublicField label="Duración aproximada" value={doc.duracion_aprox} />
        <PublicField label="Fecha y hora"        value={doc.fecha_hora} />
        <PublicField label="Recursos necesarios" value={doc.recursos_necesarios} multiline />
        <PublicField label="Requisitos"          value={doc.requisitos}          multiline />
        <PublicField label="Notas"               value={doc.notas}               multiline />
      </section>
    </article>
  )
}
