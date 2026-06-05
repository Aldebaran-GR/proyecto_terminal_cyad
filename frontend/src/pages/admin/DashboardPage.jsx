import { useQuery } from '@tanstack/react-query'
import { getDashboard, getCumplimiento } from '../../api/reportes'
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

function DocGroup({ title, data }) {
  if (!data) return null
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      <div className="grid grid-cols-4 gap-3 text-center">
        {[
          { k: 'total', label: 'Total', cls: 'text-slate-700' },
          { k: 'borrador', label: 'Borrador', cls: 'text-slate-500' },
          { k: 'publicado', label: 'Publicado', cls: 'text-blue-600' },
          { k: 'enviado', label: 'Enviado', cls: 'text-emerald-600' },
        ].map(({ k, label, cls }) => (
          <div key={k}>
            <p className={`text-2xl font-bold ${cls}`}>{data[k] ?? 0}</p>
            <p className="text-xs text-slate-400">{label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function AdminDashboardPage() {
  const { user } = useAuth()

  const { data: dash, isLoading: dashLoading, error: dashError } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => getDashboard().then((r) => r.data),
    staleTime: 60_000,
  })

  const { data: cumpl, isLoading: cumplLoading } = useQuery({
    queryKey: ['cumplimiento'],
    queryFn: () => getCumplimiento().then((r) => r.data),
    staleTime: 60_000,
  })

  if (dashLoading) return <Loading />

  if (dashError) {
    return (
      <div className="p-8">
        <Alert type="error">No se pudo cargar el dashboard. Intenta recargar la página.</Alert>
      </div>
    )
  }

  const periodo = dash?.periodo

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Bienvenido, <span className="font-medium">{user?.nombre}</span>.
          {periodo && (
            <>
              {' '}Periodo activo:{' '}
              <span className="font-semibold text-indigo-600">{periodo.clave}</span>
            </>
          )}
        </p>
      </div>

      {/* Métricas globales */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          label="Profesores activos"
          value={dash?.profesores?.total_activos ?? 0}
          color="indigo"
        />
        <StatCard
          label="Formularios publicados"
          value={dash?.autoevaluacion?.formularios?.publicado ?? 0}
          color="amber"
        />
        <StatCard
          label="Respuestas enviadas"
          value={dash?.autoevaluacion?.respuestas_enviadas ?? 0}
          color="emerald"
        />
        <StatCard
          label="Cartas enviadas"
          value={dash?.cartas_tematicas?.enviado ?? 0}
          color="slate"
          sub={`de ${dash?.cartas_tematicas?.total ?? 0} total`}
        />
      </div>

      {/* Documentos */}
      <div className="grid gap-4 md:grid-cols-2">
        <DocGroup title="Cartas Temáticas" data={dash?.cartas_tematicas} />
        <DocGroup title="Requisitos de Recuperación" data={dash?.requisitos_recuperacion} />
      </div>

      {/* Cumplimiento por departamento */}
      <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h2 className="mb-4 text-sm font-semibold text-slate-700">
          Cumplimiento por Departamento
          {periodo && <span className="ml-2 text-slate-400 font-normal">— {periodo.clave}</span>}
        </h2>
        {cumplLoading ? (
          <Loading text="Cargando cumplimiento…" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="pb-2 pr-4">Departamento</th>
                  <th className="pb-2 pr-4 text-right">Profesores</th>
                  <th className="pb-2 pr-4 text-right">Carta</th>
                  <th className="pb-2 pr-4 text-right">% Carta</th>
                  <th className="pb-2 text-right">Requisito</th>
                  <th className="pb-2 text-right">% Req.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {cumpl?.por_departamento?.map((d) => (
                  <tr key={d.departamento_id} className="hover:bg-slate-50">
                    <td className="py-2 pr-4 font-medium text-slate-800">
                      <span className="text-xs text-slate-400 mr-1">{d.clave}</span>
                      {d.nombre}
                    </td>
                    <td className="py-2 pr-4 text-right text-slate-600">{d.total_profesores}</td>
                    <td className="py-2 pr-4 text-right text-slate-600">{d.con_carta_enviada}</td>
                    <td className="py-2 pr-4 text-right">
                      <PctBar value={d.pct_carta} />
                    </td>
                    <td className="py-2 text-right text-slate-600">{d.con_requisito_enviado}</td>
                    <td className="py-2 text-right">
                      <PctBar value={d.pct_requisito} />
                    </td>
                  </tr>
                ))}
                {!cumpl?.por_departamento?.length && (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-400 text-sm">
                      Sin datos de cumplimiento para este periodo.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function PctBar({ value }) {
  const pct = value ?? 0
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-400' : 'bg-rose-400'
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="h-1.5 w-16 rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-600 w-10 text-right">{pct}%</span>
    </div>
  )
}
