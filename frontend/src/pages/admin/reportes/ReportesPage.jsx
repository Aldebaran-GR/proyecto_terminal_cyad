/**
 * Reportes detallados — Admin.
 *
 * Estructura real de respuestas del backend:
 *   /reportes/dashboard/ → { periodo, profesores, cartas_tematicas, requisitos_recuperacion, autoevaluacion }
 *   /reportes/cumplimiento-licenciatura/ → { periodo, por_licenciatura: [{...}] }
 *   /reportes/autoevaluacion/ → { periodo, formularios: [{formulario_id, titulo, estado, ...}] }
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getCumplimientoLicenciatura,
  getResumenAutoevaluacion,
  getDashboard,
} from '../../../api/reportes'
import { getPeriodos } from '../../../api/catalogos'
import Loading from '../../../components/ui/Loading'
import { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

function PctBar({ value = 0, color = 'indigo' }) {
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
          className={`h-full rounded-full transition-all ${colors[color] ?? colors.indigo}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-medium text-slate-600 w-10 text-right">
        {pct.toFixed(0)}%
      </span>
    </div>
  )
}

function SectionTitle({ children }) {
  return (
    <h2 className="text-base font-semibold text-slate-800 border-b border-slate-200 pb-2 mb-4">
      {children}
    </h2>
  )
}

function StatCard({ label, value, color = 'text-slate-700' }) {
  return (
    <div className="rounded-xl bg-white border border-slate-200 p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value ?? '—'}</p>
    </div>
  )
}

export default function ReportesPage() {
  const [periodId, setPeriodId] = useState('')
  const params = periodId ? { periodo: periodId } : {}

  const { data: periodos = [] } = useQuery({
    queryKey: ['periodos'],
    queryFn: () => getPeriodos().then((r) => r.data?.results ?? r.data ?? []),
  })

  const { data: dashboard, isLoading: loadDash } = useQuery({
    queryKey: ['dashboard-rep', periodId],
    queryFn: () => getDashboard(params).then((r) => r.data),
  })

  const { data: cumplLic, isLoading: loadLic } = useQuery({
    queryKey: ['cumpl-lic', periodId],
    queryFn: () => getCumplimientoLicenciatura(params).then((r) => r.data),
  })

  const { data: resumenAE, isLoading: loadAE } = useQuery({
    queryKey: ['resumen-ae', periodId],
    queryFn: () => getResumenAutoevaluacion(params).then((r) => r.data),
  })

  // Extraer datos de las estructuras anidadas
  const periodo = dashboard?.periodo?.clave ?? resumenAE?.periodo?.clave ?? '—'
  const totalProfesores = dashboard?.profesores?.total_activos ?? 0
  const cartasTotal = dashboard?.cartas_tematicas?.total ?? 0
  const requisitosTotal = dashboard?.requisitos_recuperacion?.total ?? 0

  const licenciaturas = cumplLic?.por_licenciatura ?? []
  const formularios = resumenAE?.formularios ?? []

  return (
    <div className="p-6 space-y-8">
      {/* Header + filtro */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Reportes</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Indicadores de cumplimiento y autoevaluación.
          </p>
        </div>
        <select
          value={periodId}
          onChange={(e) => setPeriodId(e.target.value)}
          className={inputCls + ' w-40'}
        >
          <option value="">Periodo activo</option>
          {periodos.map((p) => (
            <option key={p.id} value={p.id}>{p.clave}</option>
          ))}
        </select>
      </div>

      {/* Resumen general */}
      {loadDash ? (
        <Loading />
      ) : dashboard ? (
        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Periodo" value={periodo} />
          <StatCard label="Profesores activos" value={totalProfesores} color="text-indigo-600" />
          <StatCard label="Cartas Temáticas" value={cartasTotal} color="text-slate-700" />
          <StatCard label="Req. de Recuperación" value={requisitosTotal} color="text-slate-700" />
        </div>
      ) : null}

      {/* Cumplimiento por licenciatura */}
      <div>
        <SectionTitle>Cumplimiento por Licenciatura</SectionTitle>
        {loadLic ? (
          <Loading />
        ) : (
          <div className="rounded-xl border border-slate-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Licenciatura</th>
                  <th className="px-4 py-3 text-left w-48">Cartas Temáticas</th>
                  <th className="px-4 py-3 text-left w-48">Req. Recuperación</th>
                  <th className="px-4 py-3 text-right w-28">UEAs activas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {licenciaturas.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-slate-400 text-sm">
                      Sin datos de cumplimiento para este periodo.
                    </td>
                  </tr>
                )}
                {licenciaturas.map((row) => {
                  const totalUEA = row.total_ueas_activas ?? 0
                  // Tras retirar ENVIADO, "publicados" es el indicador único.
                  const cartasPub = row.cartas_tematicas?.publicado ?? 0
                  const reqPub = row.requisitos_recuperacion?.publicado ?? 0
                  const pctCarta = totalUEA > 0 ? (cartasPub / totalUEA) * 100 : 0
                  const pctReq = totalUEA > 0 ? (reqPub / totalUEA) * 100 : 0

                  return (
                    <tr key={row.licenciatura_id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-medium text-slate-800">
                        {row.nombre}
                        <span className="ml-2 text-xs text-slate-400">{row.clave}</span>
                      </td>
                      <td className="px-4 py-3">
                        <PctBar value={pctCarta} color="indigo" />
                        <p className="text-xs text-slate-400 mt-0.5">
                          {cartasPub}/{totalUEA} UEAs
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        <PctBar value={pctReq} color="emerald" />
                        <p className="text-xs text-slate-400 mt-0.5">
                          {reqPub}/{totalUEA} UEAs
                        </p>
                      </td>
                      <td className="px-4 py-3 text-right text-slate-600">{totalUEA}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Resumen autoevaluaciones */}
      <div>
        <SectionTitle>Resumen de Autoevaluaciones</SectionTitle>
        {loadAE ? (
          <Loading />
        ) : (
          <div className="space-y-4">
            {formularios.length === 0 && (
              <p className="text-sm text-slate-400 italic">
                Sin formularios publicados en este periodo.
              </p>
            )}
            {formularios.map((f) => {
              const pct =
                f.total_profesores > 0
                  ? ((f.respuestas_enviadas / f.total_profesores) * 100).toFixed(0)
                  : null

              return (
                <div
                  key={f.formulario_id}
                  className="rounded-xl border border-slate-200 bg-white p-5"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="font-semibold text-slate-900">{f.titulo}</p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {resumenAE?.periodo?.clave ?? '—'}
                      </p>
                    </div>
                    <Badge label={f.estado} variant={f.estado} />
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <p className="text-2xl font-bold text-indigo-600">
                        {f.respuestas_enviadas}
                      </p>
                      <p className="text-xs text-slate-500">Respuestas enviadas</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-slate-700">{f.total_profesores}</p>
                      <p className="text-xs text-slate-500">Profesores activos</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-emerald-600">
                        {pct != null ? `${pct}%` : '—'}
                      </p>
                      <p className="text-xs text-slate-500">Tasa de respuesta</p>
                    </div>
                  </div>
                  {pct != null && (
                    <div className="mt-3">
                      <PctBar value={Number(pct)} color="emerald" />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
