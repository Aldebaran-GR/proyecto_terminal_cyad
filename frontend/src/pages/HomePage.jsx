/**
 * Home pública — solo elige el tipo de documento a consultar.
 *
 * Todo el flujo de cascada (periodo → programa → UEA → docs) vive en
 * `/publico/explorar/:tipo`. Esta página se mantiene minimalista para reducir
 * carga cognitiva al visitante.
 */
import { Link } from 'react-router-dom'

const TIPOS = [
  {
    key: 'cartas',
    label: 'Carta Temática',
    descripcion:
      'Planeación académica del trimestre por UEA y grupo: objetivos, contenido, evaluación y bibliografía.',
  },
  {
    key: 'requisitos',
    label: 'Evaluación de Recuperación',
    descripcion:
      'Requisitos, lugar, fecha y recursos para la evaluación de recuperación de una UEA.',
  },
]

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

function TipoCard({ tipo }) {
  return (
    <Link
      to={`/publico/explorar/${tipo.key}`}
      className="block rounded-xl border border-slate-200 bg-white p-6 transition-all hover:border-indigo-300 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-900">{tipo.label}</p>
          <p className="mt-2 text-sm text-slate-600">{tipo.descripcion}</p>
        </div>
        <span className="shrink-0 rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
          Consultar →
        </span>
      </div>
    </Link>
  )
}

export default function HomePage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Header />

      <main className="mx-auto max-w-5xl px-6 py-10 space-y-6">
        <section>
          <h2 className="text-lg font-semibold text-slate-800">
            ¿Qué documento deseas consultar?
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Elige el tipo de documento para explorar por periodo, licenciatura o
            posgrado, y UEA.
          </p>
        </section>

        <section className="grid gap-4 sm:grid-cols-2">
          {TIPOS.map((t) => (
            <TipoCard key={t.key} tipo={t} />
          ))}
        </section>
      </main>

      <footer className="mx-auto max-w-5xl px-6 py-6 text-center text-xs text-slate-400">
        Sistema de Proyecto Terminal CyAD — UAM Azcapotzalco
      </footer>
    </div>
  )
}
