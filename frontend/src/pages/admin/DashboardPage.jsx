import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as XLSX from 'xlsx'
import { getDashboard, getCumplimiento, getAutoevaluacionProfesores } from '../../api/reportes'
import { getCartas, getRequisitos } from '../../api/documentos'
import { getLicenciaturas, getDepartamentos } from '../../api/catalogos'
import Loading from '../../components/ui/Loading'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { inputCls } from '../../components/ui/FormField'
import { useAuth } from '../../auth/AuthContext'

// Mapea una fila de documento (Carta o Requisito) a las columnas del Excel.
// El enlace solo se llena para documentos PUBLICADO — los BORRADOR no tienen
// página pública.
function rowToExcel(row, publicPath) {
  const enlace = row.estado === 'PUBLICADO'
    ? `${window.location.origin}/publico/${publicPath}/${row.id}`
    : ''
  return {
    Profesor: row.profesor_nombre ?? '',
    Económico: row.profesor_economico ?? '',
    UEA: row.uea_nombre ?? '',
    Grupo: row.nombre_grupo ?? '',
    Estado: row.estado ?? '',
    Actualizada: row.updated_at ? new Date(row.updated_at).toLocaleDateString('es-MX') : '',
    Enlace: enlace,
    Licenciatura: row.licenciatura_nombre ?? row.posgrado_nombre ?? '',
    Departamento: row.departamento_nombre ?? '',
  }
}

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
      <div className="grid grid-cols-3 gap-3 text-center">
        {[
          { k: 'total', label: 'Total', cls: 'text-slate-700' },
          { k: 'borrador', label: 'Borrador', cls: 'text-slate-500' },
          { k: 'publicado', label: 'Publicado', cls: 'text-emerald-600' },
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
  const [filtroLic, setFiltroLic] = useState('')
  const [filtroDepto, setFiltroDepto] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState(null)

  const [filtroDeptoAE, setFiltroDeptoAE] = useState('')
  const [downloadingAE, setDownloadingAE] = useState(false)
  const [downloadErrorAE, setDownloadErrorAE] = useState(null)

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

  const { data: lics = [] } = useQuery({
    queryKey: ['licenciaturas'],
    queryFn: () => getLicenciaturas().then((r) => r.data?.results ?? r.data ?? []),
    staleTime: 5 * 60_000,
  })
  const { data: deptos = [] } = useQuery({
    queryKey: ['departamentos'],
    queryFn: () => getDepartamentos().then((r) => r.data?.results ?? r.data ?? []),
    staleTime: 5 * 60_000,
  })

  // Descarga un .xlsx con dos hojas (Cartas Temáticas + Requisitos), aplicando
  // los filtros de licenciatura (de la UEA) y departamento (del profesor).
  // page_size=200 = max_page_size actual; con la data demo bastan, y un TODO
  // queda anotado por si más adelante hay que paginar.
  // Nota seguridad: la lib `xlsx` (SheetJS community) tiene vulns reportadas
  // que solo afectan el *parseo* de XLSX externos; aquí solo escribimos
  // archivos desde data ya validada por el backend.
  async function descargarExcel() {
    setDownloadError(null)
    setDownloading(true)
    try {
      const params = { page_size: 200 }
      if (filtroLic) params.uea__licenciatura = filtroLic
      if (filtroDepto) params.profesor__departamento = filtroDepto

      const [cartasRes, reqsRes] = await Promise.all([
        getCartas(params),
        getRequisitos(params),
      ])
      const cartas = cartasRes.data?.results ?? cartasRes.data ?? []
      const reqs = reqsRes.data?.results ?? reqsRes.data ?? []

      const wb = XLSX.utils.book_new()
      const wsCartas = XLSX.utils.json_to_sheet(cartas.map((r) => rowToExcel(r, 'cartas')))
      const wsReqs = XLSX.utils.json_to_sheet(reqs.map((r) => rowToExcel(r, 'requisitos')))
      XLSX.utils.book_append_sheet(wb, wsCartas, 'Cartas Temáticas')
      XLSX.utils.book_append_sheet(wb, wsReqs, 'Requisitos')

      const fecha = new Date().toISOString().slice(0, 10)
      XLSX.writeFile(wb, `informe_documentos_${fecha}.xlsx`)
    } catch (e) {
      setDownloadError(e?.response?.data?.detail || e?.message || 'No se pudo generar el Excel.')
    } finally {
      setDownloading(false)
    }
  }

  // Descarga un .xlsx con la puntuación de autoevaluación de cada profesor
  // activo (0% si no la han enviado), su número económico y departamento.
  // Filtra opcionalmente por departamento del profesor.
  async function descargarExcelAutoevaluaciones() {
    setDownloadErrorAE(null)
    setDownloadingAE(true)
    try {
      const params = {}
      if (filtroDeptoAE) params.departamento = filtroDeptoAE

      const res = await getAutoevaluacionProfesores(params)
      const profesores = res.data?.profesores ?? []

      const rows = profesores.map((p) => ({
        Profesor: p.nombre_completo ?? '',
        Económico: p.numero_economico ?? '',
        Departamento: p.departamento_nombre ?? '',
        'Puntuación (%)': p.porcentaje ?? 0,
      }))

      const wb = XLSX.utils.book_new()
      const ws = XLSX.utils.json_to_sheet(rows)
      XLSX.utils.book_append_sheet(wb, ws, 'Autoevaluaciones')

      const fecha = new Date().toISOString().slice(0, 10)
      XLSX.writeFile(wb, `informe_autoevaluaciones_${fecha}.xlsx`)
    } catch (e) {
      setDownloadErrorAE(e?.response?.data?.detail || e?.message || 'No se pudo generar el Excel.')
    } finally {
      setDownloadingAE(false)
    }
  }

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
          label="Cartas publicadas"
          value={dash?.cartas_tematicas?.publicado ?? 0}
          color="slate"
          sub={`de ${dash?.cartas_tematicas?.total ?? 0} total`}
        />
      </div>

      {/* Documentos */}
      <div className="grid gap-4 md:grid-cols-2">
        <DocGroup title="Cartas Temáticas" data={dash?.cartas_tematicas} />
        <DocGroup title="Requisitos de Recuperación" data={dash?.requisitos_recuperacion} />
      </div>

      {/* Descargar informe en Excel */}
      <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h2 className="mb-1 text-sm font-semibold text-slate-700">Descargar informe</h2>
        <p className="mb-4 text-xs text-slate-500">
          Genera un Excel con dos hojas (Cartas Temáticas y Requisitos) con todos
          los documentos de la administración. Filtra opcionalmente por la
          licenciatura de la UEA o por el departamento del profesor.
        </p>
        {downloadError && (
          <Alert type="error" onClose={() => setDownloadError(null)}>{downloadError}</Alert>
        )}
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[220px]">
            <label className="block text-xs font-medium text-slate-600 mb-1">Licenciatura (de la UEA)</label>
            <select value={filtroLic} onChange={(e) => setFiltroLic(e.target.value)} className={inputCls}>
              <option value="">— Todas —</option>
              {lics.map((l) => <option key={l.id} value={l.id}>{l.nombre}</option>)}
            </select>
          </div>
          <div className="min-w-[220px]">
            <label className="block text-xs font-medium text-slate-600 mb-1">Departamento (del profesor)</label>
            <select value={filtroDepto} onChange={(e) => setFiltroDepto(e.target.value)} className={inputCls}>
              <option value="">— Todos —</option>
              {deptos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
            </select>
          </div>
          <Button onClick={descargarExcel} loading={downloading}>
            Descargar Excel
          </Button>
          {(filtroLic || filtroDepto) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setFiltroLic(''); setFiltroDepto('') }}
            >
              Limpiar filtros
            </Button>
          )}
        </div>
      </div>

      {/* Descargar reporte de autoevaluaciones */}
      <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h2 className="mb-1 text-sm font-semibold text-slate-700">Descargar autoevaluaciones</h2>
        <p className="mb-4 text-xs text-slate-500">
          Genera un Excel con la puntuación de autoevaluación de cada profesor
          activo en el periodo (0% si aún no la contesta), su número económico
          y su departamento. Filtra opcionalmente por departamento.
        </p>
        {downloadErrorAE && (
          <Alert type="error" onClose={() => setDownloadErrorAE(null)}>{downloadErrorAE}</Alert>
        )}
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[220px]">
            <label className="block text-xs font-medium text-slate-600 mb-1">Departamento</label>
            <select value={filtroDeptoAE} onChange={(e) => setFiltroDeptoAE(e.target.value)} className={inputCls}>
              <option value="">— Todos —</option>
              {deptos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
            </select>
          </div>
          <Button onClick={descargarExcelAutoevaluaciones} loading={downloadingAE}>
            Descargar Excel
          </Button>
          {filtroDeptoAE && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFiltroDeptoAE('')}
            >
              Limpiar filtro
            </Button>
          )}
        </div>
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
                    <td className="py-2 pr-4 text-right text-slate-600">{d.con_carta_publicada}</td>
                    <td className="py-2 pr-4 text-right">
                      <PctBar value={d.pct_carta} />
                    </td>
                    <td className="py-2 text-right text-slate-600">{d.con_requisito_publicado}</td>
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
