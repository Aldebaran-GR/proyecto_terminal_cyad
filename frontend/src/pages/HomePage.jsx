/**
 * Vista pública principal — Home.
 *
 * Es la primera página que ve cualquier visitante (sin login). Permite
 * explorar los documentos PUBLICADOS en cascada:
 *   1) Tipo de documento (Carta Temática | Evaluación de Recuperación)
 *   2) Licenciatura
 *   3) UEA
 *   4) Lista de documentos disponibles por grupo + profesor
 *
 * Al pulsar uno, se abre la vista pública detallada existente
 * (`/publico/cartas/:id` o `/publico/requisitos/:id`).
 *
 * En la esquina superior derecha aparece **Iniciar sesión** para profesores
 * y administradores que necesitan acceder a su área protegida.
 */
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  getPublicCartas,
  getPublicLicenciaturas,
  getPublicRequisitos,
  getPublicUEA,
} from '../api/publico'

const TIPOS = [
  {
    key: 'carta',
    label: 'Carta Temática',
    descripcion: 'Planeación académica por UEA y grupo.',
    color: 'indigo',
  },
  {
    key: 'requisito',
    label: 'Evaluación de Recuperación',
    descripcion: 'Requisitos y condiciones para la evaluación de recuperación.',
    color: 'teal',
  },
]

function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString('es-MX', {
      day: '2-digit', month: 'short', year: 'numeric',
    })
  } catch { return iso }
}

/* ─── Tarjeta de tipo de documento ───────────────────────────────────── */
function TipoCard({ tipo, selected, onClick }) {
  const cls = selected
    ? 'border-indigo-500 ring-2 ring-indigo-300 bg-indigo-50'
    : 'border-slate-200 hover:border-indigo-300 bg-white'
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border p-5 text-left transition-all ${cls}`}
    >
      <p className="text-sm font-semibold text-slate-900">{tipo.label}</p>
      <p className="mt-1 text-xs text-slate-500">{tipo.descripcion}</p>
    </button>
  )
}

/* ─── Header ─────────────────────────────────────────────────────────── */
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

/* ─── Card de documento en el listado final ──────────────────────────── */
function DocumentoCard({ doc, tipoKey }) {
  const ruta = tipoKey === 'carta'
    ? `/publico/cartas/${doc.id}`
    : `/publico/requisitos/${doc.id}`
  return (
    <Link
      to={ruta}
      className="block rounded-xl border border-slate-200 bg-white p-5 hover:border-indigo-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wider text-slate-500">
            {doc.periodo_clave} · Grupo {doc.nombre_grupo}
          </p>
          <p className="mt-1 font-semibold text-slate-900 truncate">
            {doc.profesor_nombre}
          </p>
          <p className="mt-1 text-sm text-slate-500 truncate">
            ID grupo {doc.id_grupo} · {doc.horario}
            {doc.modalidad && ` · ${doc.modalidad}`}
          </p>
        </div>
        <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 shrink-0">
          Ver documento →
        </span>
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Publicado el {formatDate(doc.created_at)}
      </p>
    </Link>
  )
}

/* ─── Página principal ───────────────────────────────────────────────── */
export default function HomePage() {
  const [tipoKey, setTipoKey] = useState(null)   // 'carta' | 'requisito'
  const [licId, setLicId] = useState('')
  const [ueaId, setUeaId] = useState('')

  /* Catálogos públicos */
  const { data: licenciaturas = [] } = useQuery({
    queryKey: ['public-licenciaturas'],
    queryFn: () => getPublicLicenciaturas().then((r) => r.data),
    staleTime: 60_000,
  })
  const { data: ueas = [] } = useQuery({
    queryKey: ['public-uea', licId],
    queryFn: () => getPublicUEA({ licenciatura: licId }).then((r) => r.data),
    enabled: !!licId,
    staleTime: 60_000,
  })

  /* Lista de documentos */
  const fetcher = tipoKey === 'carta' ? getPublicCartas : getPublicRequisitos
  const { data: documentos = [], isFetching } = useQuery({
    queryKey: ['public-documentos', tipoKey, licId, ueaId],
    queryFn: () =>
      fetcher({ licenciatura: licId || undefined, uea: ueaId || undefined })
        .then((r) => r.data),
    enabled: !!(tipoKey && licId && ueaId),
    refetchInterval: 15_000, // refresca por si el profesor publica algo nuevo
  })

  /* Reset en cascada cuando el usuario cambia un nivel anterior */
  const handleTipo = (key) => {
    setTipoKey(key)
    setLicId('')
    setUeaId('')
  }
  const handleLic = (id) => {
    setLicId(id)
    setUeaId('')
  }

  const tipoElegido = useMemo(
    () => TIPOS.find((t) => t.key === tipoKey),
    [tipoKey],
  )

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />

      <main className="mx-auto max-w-5xl px-6 py-8 space-y-8">
        {/* Paso 1 — Tipo */}
        <section>
          <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">
            Paso 1
          </p>
          <h2 className="text-lg font-semibold text-slate-800 mb-3">
            ¿Qué documento deseas consultar?
          </h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {TIPOS.map((t) => (
              <TipoCard
                key={t.key}
                tipo={t}
                selected={tipoKey === t.key}
                onClick={() => handleTipo(t.key)}
              />
            ))}
          </div>
        </section>

        {/* Paso 2 — Licenciatura */}
        {tipoKey && (
          <section>
            <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">
              Paso 2
            </p>
            <h2 className="text-lg font-semibold text-slate-800 mb-3">
              Selecciona la licenciatura
            </h2>
            <select
              value={licId}
              onChange={(e) => handleLic(e.target.value)}
              className="w-full max-w-lg rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">-- Selecciona --</option>
              {licenciaturas.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.clave} — {l.nombre}
                </option>
              ))}
            </select>
          </section>
        )}

        {/* Paso 3 — UEA */}
        {tipoKey && licId && (
          <section>
            <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">
              Paso 3
            </p>
            <h2 className="text-lg font-semibold text-slate-800 mb-3">
              Selecciona la UEA
            </h2>
            <select
              value={ueaId}
              onChange={(e) => setUeaId(e.target.value)}
              className="w-full max-w-lg rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">-- Selecciona --</option>
              {ueas.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.clave} — {u.nombre}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-400">
              {ueas.length} UEA{ueas.length === 1 ? '' : 's'} en esta licenciatura.
            </p>
          </section>
        )}

        {/* Paso 4 — Lista de documentos */}
        {tipoKey && licId && ueaId && (
          <section>
            <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">
              Documentos disponibles
            </p>
            <h2 className="text-lg font-semibold text-slate-800 mb-3">
              {tipoElegido?.label} para la UEA seleccionada
            </h2>
            {isFetching && documentos.length === 0 ? (
              <p className="text-sm text-slate-400">Cargando documentos…</p>
            ) : documentos.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
                <p className="text-sm text-slate-700 font-medium">
                  Sin documentos publicados.
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Aún no hay documentos publicados de este tipo para la UEA seleccionada.
                </p>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {documentos.map((d) => (
                  <DocumentoCard key={d.id} doc={d} tipoKey={tipoKey} />
                ))}
              </div>
            )}
          </section>
        )}

        {/* Estado inicial — placeholder */}
        {!tipoKey && (
          <p className="text-sm text-slate-500 italic">
            Comienza eligiendo el tipo de documento.
          </p>
        )}
      </main>

      <footer className="mx-auto max-w-5xl px-6 py-6 text-center text-xs text-slate-400">
        Sistema de Proyecto Terminal CyAD — UAM Azcapotzalco
      </footer>
    </div>
  )
}
