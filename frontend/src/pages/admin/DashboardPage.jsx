import { useQuery } from '@tanstack/react-query'
import { getDashboard } from '../../api/reportes'
import { getPeriodosActivos } from '../../api/catalogos'
import Loading from '../../components/ui/Loading'
import Alert from '../../components/ui/Alert'
import { useAuth } from '../../auth/AuthContext'

function StatCard({ label, value, sub, color = 'indigo' }) {
  const colors = {
    indigo: 'bg-indigo-50 text-indigo-700',
    emerald: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    rose: 'bg-rose-50 text-rose-700',
    slate: 'bg-slate-50 text-slate-700',
  }
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${colors[color]}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
    </div>
  )
}

// Bloque de métricas de un recurso (Cartas, Requisitos o Autoevaluación),
// cada uno consultado con el periodo activo propio de ese recurso — pueden
// ser 3 periodos distintos simultáneamente.
function RecursoCard({ titulo, periodo, isLoading, data }) {
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">{titulo}</h3>
        {periodo ? (
          <span className="text-xs font-medium text-indigo-600">{periodo.clave}</span>
        ) : (
          <span className="text-xs text-slate-400">Sin periodo activo</span>
        )}
      </div>
      {!periodo ? (
        <p className="text-xs text-slate-400">
          No hay periodo activo para este recurso.
        </p>
      ) : isLoading ? (
        <Loading text="Cargando…" />
      ) : (
        <div className="grid grid-cols-3 gap-3 text-center">
          {[
            { k: 'total', label: 'Total', cls: 'text-slate-700' },
            { k: 'borrador', label: 'Borrador', cls: 'text-slate-500' },
            { k: 'publicado', label: 'Publicado', cls: 'text-emerald-600' },
          ].map(({ k, label, cls }) => (
            <div key={k}>
              <p className={`text-2xl font-bold ${cls}`}>{data?.[k] ?? 0}</p>
              <p className="text-xs text-slate-400">{label}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function AdminDashboardPage() {
  const { user } = useAuth()

  const { data: activos, isLoading: activosLoading, error: activosError } = useQuery({
    queryKey: ['periodos-activos'],
    queryFn: () => getPeriodosActivos().then((r) => r.data),
    staleTime: 60_000,
  })

  const periodoCartas = activos?.cartas ?? null
  const periodoRequisitos = activos?.requisitos ?? null
  const periodoAE = activos?.autoevaluacion ?? null

  const { data: dashCartas, isLoading: loadCartas } = useQuery({
    queryKey: ['dashboard', 'cartas', periodoCartas?.id],
    queryFn: () => getDashboard({ periodo: periodoCartas.id }).then((r) => r.data),
    enabled: !!periodoCartas,
  })
  const { data: dashRequisitos, isLoading: loadRequisitos } = useQuery({
    queryKey: ['dashboard', 'requisitos', periodoRequisitos?.id],
    queryFn: () => getDashboard({ periodo: periodoRequisitos.id }).then((r) => r.data),
    enabled: !!periodoRequisitos,
  })
  const { data: dashAE, isLoading: loadAE } = useQuery({
    queryKey: ['dashboard', 'autoevaluacion', periodoAE?.id],
    queryFn: () => getDashboard({ periodo: periodoAE.id }).then((r) => r.data),
    enabled: !!periodoAE,
  })

  if (activosLoading) return <Loading />

  if (activosError) {
    return (
      <div className="p-8">
        <Alert type="error">No se pudo cargar el dashboard. Intenta recargar la página.</Alert>
      </div>
    )
  }

  const totalProfesores = dashCartas?.profesores?.total_activos
    ?? dashRequisitos?.profesores?.total_activos
    ?? dashAE?.profesores?.total_activos
    ?? 0

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Bienvenido, <span className="font-medium">{user?.nombre}</span>.
        </p>
      </div>

      {/* Métrica transversal */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Profesores activos" value={totalProfesores} color="indigo" />
        <StatCard
          label="Respuestas enviadas"
          value={dashAE?.autoevaluacion?.respuestas_enviadas ?? 0}
          color="emerald"
        />
        <StatCard
          label="Formularios publicados"
          value={dashAE?.autoevaluacion?.formularios?.publicado ?? 0}
          color="amber"
        />
        <StatCard
          label="Cartas publicadas"
          value={dashCartas?.cartas_tematicas?.publicado ?? 0}
          color="slate"
          sub={`de ${dashCartas?.cartas_tematicas?.total ?? 0} total`}
        />
      </div>

      {/* Métricas por recurso, cada una con su propio periodo activo */}
      <div className="grid gap-4 md:grid-cols-3">
        <RecursoCard
          titulo="Cartas Temáticas"
          periodo={periodoCartas}
          isLoading={loadCartas}
          data={dashCartas?.cartas_tematicas}
        />
        <RecursoCard
          titulo="Requisitos de Recuperación"
          periodo={periodoRequisitos}
          isLoading={loadRequisitos}
          data={dashRequisitos?.requisitos_recuperacion}
        />
        <RecursoCard
          titulo="Autoevaluación"
          periodo={periodoAE}
          isLoading={loadAE}
          data={dashAE?.autoevaluacion?.formularios}
        />
      </div>
    </div>
  )
}
