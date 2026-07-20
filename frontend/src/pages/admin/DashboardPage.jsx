import { useQuery } from '@tanstack/react-query'
import { getDashboard, getCumplimiento, getResumenAutoevaluacion } from '../../api/reportes'
import { getPeriodosActivos } from '../../api/catalogos'
import Loading from '../../components/ui/Loading'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import { useAuth } from '../../auth/AuthContext'

function StatCard({ label, value, sub, color = 'indigo', periodo }) {
  const colors = {
    indigo: 'bg-indigo-50 text-indigo-700',
    emerald: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    rose: 'bg-rose-50 text-rose-700',
    slate: 'bg-slate-50 text-slate-700',
  }
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">{label}</p>
        {periodo && <span className="text-xs font-medium text-indigo-600">{periodo.clave}</span>}
      </div>
      <p className={`mt-1 text-3xl font-bold ${colors[color]}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
    </div>
  )
}

function PctBar({ value = 0, color = 'emerald' }) {
  const colors = {
    indigo: 'bg-indigo-500',
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-400',
    rose: 'bg-rose-500',
  }
  const pct = Math.min(100, Math.max(0, value ?? 0))
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${colors[color] ?? colors.emerald}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-medium text-slate-600 w-10 text-right">
        {pct.toFixed(0)}%
      </span>
    </div>
  )
}

// Bloque de un documento (Cartas o Requisitos): cumplimiento por departamento.
// No se muestra porcentaje de cumplimiento — un profesor puede tener varios
// documentos (uno por UEA), así que "profesores con doc / total" no
// representa un cumplimiento real; solo se listan los conteos. Los conteos
// generales (total/borrador/publicado) ya se muestran en las StatCards de
// arriba, así que aquí no se repiten.
function CumplimientoDocCard({ titulo, periodo, cumplLoading, cumplData, campoConteo }) {
  const porDepartamento = cumplData?.por_departamento ?? []

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
      ) : (
        <>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Cumplimiento por departamento
          </h4>
          {cumplLoading ? (
            <Loading text="Cargando…" />
          ) : (
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                  <tr>
                    <th className="px-3 py-2 text-left">Departamento</th>
                    <th className="px-3 py-2 text-right">Profesores</th>
                    <th className="px-3 py-2 text-right">{titulo === 'Cartas Temáticas' ? 'Carta' : 'Requisito'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {porDepartamento.length === 0 && (
                    <tr>
                      <td colSpan={3} className="px-3 py-6 text-center text-slate-400 text-sm">
                        Sin datos de cumplimiento para este periodo.
                      </td>
                    </tr>
                  )}
                  {porDepartamento.map((d) => (
                    <tr key={d.departamento_id} className="hover:bg-slate-50">
                      <td className="px-3 py-2 font-medium text-slate-800">
                        <span className="text-xs text-slate-400 mr-1">{d.clave}</span>
                        {d.nombre}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-600">
                        {d[campoConteo]}/{d.total_profesores}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-600">{d[campoConteo]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// Bloque de Autoevaluación: una sub-tarjeta por formulario del periodo activo,
// con respuestas enviadas / profesores activos / tasa de respuesta.
function AutoevaluacionCard({ periodo, isLoading, formularios }) {
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Autoevaluación</h3>
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
      ) : !formularios?.length ? (
        <p className="text-xs text-slate-400">Sin formularios en este periodo.</p>
      ) : (
        <div className="space-y-4">
          {formularios.map((f) => (
            <div key={f.formulario_id} className="rounded-lg border border-slate-200 p-4">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-medium text-slate-800">{f.titulo}</p>
                <Badge label={f.estado} variant={f.estado} />
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="text-xl font-bold text-indigo-600">{f.respuestas_enviadas}</p>
                  <p className="text-xs text-slate-400">Respuestas</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-slate-700">{f.total_profesores}</p>
                  <p className="text-xs text-slate-400">Profesores activos</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-emerald-600">{f.tasa_respuesta ?? 0}%</p>
                  <p className="text-xs text-slate-400">Tasa de respuesta</p>
                </div>
              </div>
              <div className="mt-3">
                <PctBar value={f.tasa_respuesta ?? 0} />
              </div>
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

  const { data: dashCartas } = useQuery({
    queryKey: ['dashboard', 'cartas', periodoCartas?.id],
    queryFn: () => getDashboard({ periodo: periodoCartas.id }).then((r) => r.data),
    enabled: !!periodoCartas,
  })
  const { data: dashRequisitos } = useQuery({
    queryKey: ['dashboard', 'requisitos', periodoRequisitos?.id],
    queryFn: () => getDashboard({ periodo: periodoRequisitos.id }).then((r) => r.data),
    enabled: !!periodoRequisitos,
  })
  const { data: dashAE } = useQuery({
    queryKey: ['dashboard', 'autoevaluacion', periodoAE?.id],
    queryFn: () => getDashboard({ periodo: periodoAE.id }).then((r) => r.data),
    enabled: !!periodoAE,
  })

  const { data: cumplCartas, isLoading: loadCumplCartas } = useQuery({
    queryKey: ['cumpl-depto', 'cartas', periodoCartas?.id],
    queryFn: () => getCumplimiento({ periodo: periodoCartas.id }).then((r) => r.data),
    enabled: !!periodoCartas,
  })
  const { data: cumplRequisitos, isLoading: loadCumplRequisitos } = useQuery({
    queryKey: ['cumpl-depto', 'requisitos', periodoRequisitos?.id],
    queryFn: () => getCumplimiento({ periodo: periodoRequisitos.id }).then((r) => r.data),
    enabled: !!periodoRequisitos,
  })

  const { data: resumenAE, isLoading: loadResumenAE } = useQuery({
    queryKey: ['resumen-ae', periodoAE?.id],
    queryFn: () => getResumenAutoevaluacion({ periodo: periodoAE.id }).then((r) => r.data),
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
          label="Cartas temáticas"
          value={dashCartas?.cartas_tematicas?.publicado ?? 0}
          sub="Publicadas"
          color="slate"
          periodo={periodoCartas}
        />
        <StatCard
          label="Requisitos"
          value={dashRequisitos?.requisitos_recuperacion?.publicado ?? 0}
          sub="Publicados"
          color="emerald"
          periodo={periodoRequisitos}
        />
        <StatCard
          label="Formularios publicados"
          value={dashAE?.autoevaluacion?.formularios?.publicado ?? 0}
          color="amber"
          periodo={periodoAE}
        />
      </div>

      {/* Cartas y Requisitos: cumplimiento por departamento */}
      <div className="grid gap-4 lg:grid-cols-2">
        <CumplimientoDocCard
          titulo="Cartas Temáticas"
          periodo={periodoCartas}
          cumplLoading={loadCumplCartas}
          cumplData={cumplCartas}
          campoConteo="con_carta_publicada"
        />
        <CumplimientoDocCard
          titulo="Requisitos de Recuperación"
          periodo={periodoRequisitos}
          cumplLoading={loadCumplRequisitos}
          cumplData={cumplRequisitos}
          campoConteo="con_requisito_publicado"
        />
      </div>

      {/* Autoevaluación: respuestas / profesores / tasa por formulario */}
      <AutoevaluacionCard
        periodo={periodoAE}
        isLoading={loadResumenAE}
        formularios={resumenAE?.formularios}
      />
    </div>
  )
}
