/**
 * Página pública de exploración de documentos publicados.
 *
 * Ruta: /publico/explorar/:tipo   (tipo ∈ { cartas, requisitos })
 *
 * Flujo (todo con estado interno, sin sub-rutas):
 *   1. Elegir periodo (solo aquellos con ≥1 documento publicado del tipo).
 *   2. Elegir Licenciatura o Posgrado (solo se listan los activos).
 *   3. Ver UEA con documento publicado en ese periodo/programa:
 *        - Posgrado → un solo bloque, sin agrupar.
 *        - Licenciatura → agrupar por regla:
 *            area.nombre === 'Licenciatura'  → por trimestre (1..N; '' → "Sin trimestre definido")
 *            area && area.nombre !== 'Licenciatura' → por area.nombre (solo nombre)
 *            area === null → sección "Sin área definida"
 *   4. Click en la UEA → acordeón con cards de sus documentos publicados
 *      (grupo, profesor, fecha de publicación = updated_at, enlace).
 *
 * Un banner permanente aclara que solo se muestran UEA con documento publicado.
 */
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  getPublicCartas,
  getPublicLicenciaturas,
  getPublicPeriodos,
  getPublicPosgrados,
  getPublicRequisitos,
  getPublicUEA,
} from '../../api/publico'
import Alert from '../../components/ui/Alert'

const TIPOS = {
  cartas:     { key: 'cartas',     apiKey: 'carta',     label: 'Carta Temática',            detalleRuta: (id) => `/publico/cartas/${id}`,     fetchDocs: getPublicCartas },
  requisitos: { key: 'requisitos', apiKey: 'requisito', label: 'Evaluación de Recuperación', detalleRuta: (id) => `/publico/requisitos/${id}`, fetchDocs: getPublicRequisitos },
}

function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString('es-MX', {
      day: '2-digit', month: 'long', year: 'numeric',
    })
  } catch { return iso }
}

/* ─── Header ─────────────────────────────────────────────────────── */
function Header() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto max-w-5xl px-6 py-4 flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-400">
            UAM Azcapotzalco · CyAD
          </p>
          <h1 className="text-base font-semibold text-slate-900">
            Documentos académicos públicos
          </h1>
        </div>
        <Link
          to="/login"
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Iniciar sesión →
        </Link>
      </div>
    </header>
  )
}

/* ─── Breadcrumbs ────────────────────────────────────────────────── */
function Crumb({ children, onClick, active = false }) {
  const cls = active
    ? 'text-slate-800 font-medium'
    : 'text-indigo-600 hover:underline cursor-pointer'
  return (
    <button
      type="button"
      onClick={active ? undefined : onClick}
      className={`text-sm ${cls}`}
      disabled={active}
    >
      {children}
    </button>
  )
}

function Breadcrumbs({ tipo, periodo, programa, uea, onResetPeriodo, onResetPrograma, onResetUEA }) {
  return (
    <nav className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
      <Link to="/" className="text-indigo-600 hover:underline">Inicio</Link>
      <span>›</span>
      <Crumb onClick={onResetPeriodo} active={!periodo}>{tipo.label}</Crumb>
      {periodo && (
        <>
          <span>›</span>
          <Crumb onClick={onResetPrograma} active={!programa}>Periodo {periodo.clave}</Crumb>
        </>
      )}
      {programa && (
        <>
          <span>›</span>
          <Crumb onClick={onResetUEA} active={!uea}>{programa.label}</Crumb>
        </>
      )}
      {uea && (
        <>
          <span>›</span>
          <Crumb active>UEA {uea.clave}</Crumb>
        </>
      )}
    </nav>
  )
}

/* ─── Card documento (dentro del acordeón) ───────────────────────── */
function DocumentoCard({ doc, tipo }) {
  return (
    <Link
      to={tipo.detalleRuta(doc.id)}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-lg border border-slate-200 bg-white p-4 hover:border-indigo-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wider text-slate-500">
            Grupo {doc.nombre_grupo}
            {doc.id_grupo && ` · ID ${doc.id_grupo}`}
          </p>
          <p className="mt-1 font-semibold text-slate-900 truncate">
            {doc.profesor_nombre}
          </p>
          <p className="mt-1 text-xs text-slate-500 truncate">
            {doc.horario}
            {doc.modalidad && ` · ${doc.modalidad}`}
          </p>
        </div>
        <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 shrink-0">
          Ver documento →
        </span>
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Publicado el {formatDate(doc.updated_at)}
      </p>
    </Link>
  )
}

/* ─── Acordeón de docs por UEA ───────────────────────────────────── */
function UEARow({ uea, tipo, periodo, programa, expanded, onToggle }) {
  const programaParams = programa.tipo === 'licenciatura'
    ? { licenciatura: programa.id }
    : { posgrado: programa.id }

  const { data: docs = [], isFetching } = useQuery({
    queryKey: ['public-docs', tipo.key, periodo.id, programa.tipo, programa.id, uea.id],
    queryFn: () =>
      tipo.fetchDocs({ ...programaParams, periodo: periodo.id, uea: uea.id })
        .then((r) => r.data),
    enabled: expanded,
    staleTime: 15_000,
  })

  return (
    <li className="border-b border-slate-100 last:border-0">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left transition-all hover:bg-indigo-50 hover:shadow-md hover:-translate-y-0.5 hover:relative hover:z-10"
      >
        <div className="min-w-0">
          <p className="text-sm font-mono text-slate-500">{uea.clave}</p>
          <p className="text-sm font-medium text-slate-800 truncate">{uea.nombre}</p>
        </div>
        <span className={`shrink-0 text-slate-400 transition-transform ${expanded ? 'rotate-90' : ''}`}>
          ›
        </span>
      </button>
      {expanded && (
        <div className="px-4 pb-4 pt-1 space-y-3 bg-slate-50/50">
          {isFetching && docs.length === 0 ? (
            <p className="text-sm text-slate-400">Cargando documentos…</p>
          ) : docs.length === 0 ? (
            <p className="text-sm text-slate-500">
              Sin documentos publicados para esta UEA en el periodo seleccionado.
            </p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {docs.map((d) => (
                <DocumentoCard key={d.id} doc={d} tipo={tipo} />
              ))}
            </div>
          )}
        </div>
      )}
    </li>
  )
}

/* ─── Card con grupo de UEAs (trimestre o área) ──────────────────── */
function UEAGroupCard({ titulo, ueas, tipo, periodo, programa, expandedId, setExpandedId }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <header className="px-4 py-3 bg-indigo-600 border-b border-indigo-700">
        <h3 className="text-sm font-semibold text-white">{titulo}</h3>
        <p className="text-xs text-indigo-100 mt-0.5">
          {ueas.length} UEA{ueas.length === 1 ? '' : 's'} con documento publicado
        </p>
      </header>
      <ul>
        {ueas.map((u) => (
          <UEARow
            key={u.id}
            uea={u}
            tipo={tipo}
            periodo={periodo}
            programa={programa}
            expanded={expandedId === u.id}
            onToggle={() => setExpandedId(expandedId === u.id ? null : u.id)}
          />
        ))}
      </ul>
    </div>
  )
}

/* ─── Agrupador (licenciatura vs posgrado) ───────────────────────── */
function agruparUEAs(ueas, programa) {
  if (programa.tipo === 'posgrado') {
    return [{ key: '__todas__', titulo: 'UEA del posgrado', ueas }]
  }
  // Licenciatura → por regla acordada.
  const porTrimestre = new Map()     // trimestre → [ueas]
  const porArea = new Map()          // area.nombre → [ueas]
  const sinArea = []

  for (const u of ueas) {
    if (u.area === null || u.area === undefined) {
      sinArea.push(u)
      continue
    }
    if (u.area_nombre === 'Licenciatura') {
      const key = (u.trimestre ?? '').toString().trim()
      const bucket = porTrimestre.get(key) ?? []
      bucket.push(u)
      porTrimestre.set(key, bucket)
    } else {
      const key = u.area_nombre || 'Otra'
      const bucket = porArea.get(key) ?? []
      bucket.push(u)
      porArea.set(key, bucket)
    }
  }

  const grupos = []

  // Trimestres numéricos ordenados; "" al final ("Sin trimestre definido").
  const trimestreKeys = Array.from(porTrimestre.keys())
  const numericos = trimestreKeys
    .filter((k) => k !== '' && !Number.isNaN(Number(k)))
    .sort((a, b) => Number(a) - Number(b))
  const noNumericos = trimestreKeys
    .filter((k) => k !== '' && Number.isNaN(Number(k)))
    .sort()
  const vacios = trimestreKeys.includes('') ? [''] : []
  for (const k of [...numericos, ...noNumericos, ...vacios]) {
    const titulo = k === '' ? 'Sin trimestre definido' : `Trimestre ${k}`
    grupos.push({ key: `tri-${k || 'sin'}`, titulo, ueas: porTrimestre.get(k) })
  }

  // Áreas (optativas) ordenadas alfabéticamente.
  for (const nombre of Array.from(porArea.keys()).sort()) {
    grupos.push({ key: `area-${nombre}`, titulo: nombre, ueas: porArea.get(nombre) })
  }

  if (sinArea.length) {
    grupos.push({ key: 'sin-area', titulo: 'Sin área definida', ueas: sinArea })
  }
  return grupos
}

/* ─── Página principal ───────────────────────────────────────────── */
export default function ExplorarPage() {
  const { tipo: tipoParam } = useParams()
  const tipo = TIPOS[tipoParam] ?? TIPOS.cartas

  // Estado en cascada.
  const [periodo, setPeriodo] = useState(null)   // { id, clave }
  const [programa, setPrograma] = useState(null) // { tipo: 'licenciatura'|'posgrado', id, label }
  const [expandedUEA, setExpandedUEA] = useState(null)

  /* Catálogos */
  const { data: periodos = [] } = useQuery({
    queryKey: ['public-periodos', tipo.apiKey],
    queryFn: () => getPublicPeriodos(tipo.apiKey).then((r) => r.data),
    staleTime: 60_000,
  })
  const { data: licenciaturas = [] } = useQuery({
    queryKey: ['public-licenciaturas'],
    queryFn: () => getPublicLicenciaturas().then((r) => r.data),
    staleTime: 60_000,
  })
  const { data: posgrados = [] } = useQuery({
    queryKey: ['public-posgrados'],
    queryFn: () => getPublicPosgrados().then((r) => r.data),
    staleTime: 60_000,
  })

  /* UEAs con documento del tipo/periodo/programa */
  const programaParams = useMemo(() => {
    if (!programa) return null
    return programa.tipo === 'licenciatura'
      ? { licenciatura: programa.id }
      : { posgrado: programa.id }
  }, [programa])

  const { data: ueas = [], isFetching: cargandoUeas } = useQuery({
    queryKey: ['public-uea-con-docs', tipo.apiKey, periodo?.id, programa?.tipo, programa?.id],
    queryFn: () =>
      getPublicUEA({
        ...programaParams,
        periodo: periodo.id,
        con_documentos_de: tipo.apiKey,
      }).then((r) => r.data),
    enabled: !!(periodo && programa),
    staleTime: 30_000,
  })

  /* Resets en cascada */
  const resetPeriodo = () => { setPeriodo(null); setPrograma(null); setExpandedUEA(null) }
  const resetPrograma = () => { setPrograma(null); setExpandedUEA(null) }
  const resetUEA = () => setExpandedUEA(null)

  const grupos = useMemo(
    () => (programa ? agruparUEAs(ueas, programa) : []),
    [ueas, programa],
  )

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />

      <main className="mx-auto max-w-5xl px-6 py-8 space-y-8">
        <Breadcrumbs
          tipo={tipo}
          periodo={periodo}
          programa={programa}
          uea={expandedUEA ? ueas.find((u) => u.id === expandedUEA) : null}
          onResetPeriodo={resetPeriodo}
          onResetPrograma={resetPrograma}
          onResetUEA={resetUEA}
        />

        {/* Paso 1 — Periodo */}
        <section>
          <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">Paso 1</p>
          <h2 className="text-lg font-semibold text-slate-800 mb-3">
            Selecciona el periodo
          </h2>
          <select
            value={periodo?.id ?? ''}
            onChange={(e) => {
              const p = periodos.find((x) => String(x.id) === e.target.value) ?? null
              setPeriodo(p)
              setPrograma(null)
              setExpandedUEA(null)
            }}
            className="w-full max-w-lg rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">-- Selecciona --</option>
            {periodos.map((p) => (
              <option key={p.id} value={p.id}>{p.clave}</option>
            ))}
          </select>
          {periodos.length === 0 && (
            <p className="mt-2 text-xs text-slate-400">
              Aún no hay periodos con documentos publicados de este tipo.
            </p>
          )}
        </section>

        {/* Paso 2 — Programa */}
        {periodo && (
          <section>
            <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">Paso 2</p>
            <h2 className="text-lg font-semibold text-slate-800 mb-3">
              Selecciona la licenciatura o posgrado
            </h2>

            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Licenciaturas</h3>
                {licenciaturas.length === 0 ? (
                  <p className="text-xs text-slate-400">Sin licenciaturas registradas.</p>
                ) : (
                  <div className="space-y-2">
                    {licenciaturas.map((l) => {
                      const activo = programa?.tipo === 'licenciatura' && programa.id === l.id
                      return (
                        <button
                          type="button"
                          key={l.id}
                          onClick={() => {
                            setPrograma({ tipo: 'licenciatura', id: l.id, label: l.nombre })
                            setExpandedUEA(null)
                          }}
                          className={`w-full rounded-lg border px-4 py-3 text-left text-sm transition-all ${
                            activo
                              ? 'border-indigo-500 ring-2 ring-indigo-200 bg-indigo-50'
                              : 'border-slate-200 bg-white hover:border-indigo-300'
                          }`}
                        >
                          <p className="font-semibold text-slate-900">{l.nombre}</p>
                          <p className="text-xs text-slate-500 mt-0.5 font-mono">{l.clave}</p>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>

              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Posgrados</h3>
                {posgrados.length === 0 ? (
                  <p className="text-xs text-slate-400">Sin posgrados registrados.</p>
                ) : (
                  <div className="space-y-2">
                    {posgrados.map((p) => {
                      const activo = programa?.tipo === 'posgrado' && programa.id === p.id
                      return (
                        <button
                          type="button"
                          key={p.id}
                          onClick={() => {
                            setPrograma({ tipo: 'posgrado', id: p.id, label: p.nombre })
                            setExpandedUEA(null)
                          }}
                          className={`w-full rounded-lg border px-4 py-3 text-left text-sm transition-all ${
                            activo
                              ? 'border-teal-500 ring-2 ring-teal-200 bg-teal-50'
                              : 'border-slate-200 bg-white hover:border-teal-300'
                          }`}
                        >
                          <p className="font-semibold text-slate-900">{p.nombre}</p>
                          <p className="text-xs text-slate-500 mt-0.5 font-mono">{p.clave}</p>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Paso 3 — UEAs con documento (agrupadas) */}
        {periodo && programa && (
          <section className="space-y-4">
            <p className="text-xs uppercase tracking-wider text-slate-500">Paso 3</p>
            <h2 className="text-lg font-semibold text-slate-800">
              UEA con {tipo.label.toLowerCase()} publicada
            </h2>

            <Alert type="warning">
              Solo se muestran UEA con al menos un documento publicado. Si una UEA
              no aparece es porque ningún profesor ha publicado su documento para
              este periodo.
            </Alert>

            {cargandoUeas && ueas.length === 0 ? (
              <p className="text-sm text-slate-400">Cargando UEA…</p>
            ) : grupos.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
                <p className="text-sm font-medium text-slate-700">
                  Sin UEA con documentos publicados.
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Ningún profesor de este programa ha publicado {tipo.label.toLowerCase()}
                  {' '}para el periodo {periodo.clave}.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {grupos.map((g) => (
                  <UEAGroupCard
                    key={g.key}
                    titulo={g.titulo}
                    ueas={g.ueas}
                    tipo={tipo}
                    periodo={periodo}
                    programa={programa}
                    expandedId={expandedUEA}
                    setExpandedId={setExpandedUEA}
                  />
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      <footer className="mx-auto max-w-5xl px-6 py-6 text-center text-xs text-slate-400">
        Sistema de Proyecto Terminal CyAD — UAM Azcapotzalco
      </footer>
    </div>
  )
}
