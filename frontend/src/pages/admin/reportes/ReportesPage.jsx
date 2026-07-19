/**
 * Reportes detallados — Admin.
 *
 * Cartas, Requisitos y Autoevaluación tienen cada uno su propio periodo
 * activo (ver Periodo.get_activo por recurso), así que cada sección de esta
 * página trae su propio selector de periodo — no existe un "periodo activo"
 * único para toda la administración.
 *
 * Estructura real de respuestas del backend:
 *   /reportes/dashboard/ → { periodo, profesores, cartas_tematicas, requisitos_recuperacion, autoevaluacion }
 *   /reportes/cumplimiento/ → { periodo, resumen, por_departamento: [{...}] }
 *   /reportes/cumplimiento-licenciatura/ → { periodo, por_licenciatura: [{...}] }
 *   /reportes/autoevaluacion/ → { periodo, formularios: [{formulario_id, titulo, estado, ...}] }
 *   /reportes/autoevaluacion-profesores/ → { periodo, formulario, profesores: [{...}] }
 */
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as XLSX from 'xlsx'
import {
  getCumplimiento,
  getCumplimientoLicenciatura,
  getResumenAutoevaluacion,
  getAutoevaluacionProfesores,
} from '../../../api/reportes'
import { getCartas, getRequisitos } from '../../../api/documentos'
import { getPeriodos, getPeriodosActivos, getLicenciaturas, getDepartamentos } from '../../../api/catalogos'
import Loading from '../../../components/ui/Loading'
import Alert from '../../../components/ui/Alert'
import Button from '../../../components/ui/Button'
import { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

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

function SectionTitle({ children, right }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-200 pb-2 mb-4">
      <h2 className="text-base font-semibold text-slate-800">{children}</h2>
      {right}
    </div>
  )
}

// Selector de periodo para una sección — sin opción "Periodo activo": cada
// recurso (Cartas/Requisitos/Autoevaluación) tiene su propio periodo activo,
// preseleccionado desde /periodos/activos/ al cargar la página.
function PeriodoSelect({ periodos, value, onChange }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className={inputCls + ' w-40'}>
      <option value="">Selecciona periodo</option>
      {periodos.map((p) => (
        <option key={p.id} value={p.id}>{p.clave}</option>
      ))}
    </select>
  )
}

export default function ReportesPage() {
  const [periodoCartas, setPeriodoCartas] = useState('')
  const [periodoRequisitos, setPeriodoRequisitos] = useState('')
  const [periodoAE, setPeriodoAE] = useState('')

  const [filtroLicCartas, setFiltroLicCartas] = useState('')
  const [filtroDeptoCartas, setFiltroDeptoCartas] = useState('')
  const [downloadingCartas, setDownloadingCartas] = useState(false)
  const [downloadErrorCartas, setDownloadErrorCartas] = useState(null)

  const [filtroLicReq, setFiltroLicReq] = useState('')
  const [filtroDeptoReq, setFiltroDeptoReq] = useState('')
  const [downloadingReq, setDownloadingReq] = useState(false)
  const [downloadErrorReq, setDownloadErrorReq] = useState(null)

  const [filtroDeptoAE, setFiltroDeptoAE] = useState('')
  const [downloadingAE, setDownloadingAE] = useState(false)
  const [downloadErrorAE, setDownloadErrorAE] = useState(null)

  const { data: periodos = [] } = useQuery({
    queryKey: ['periodos'],
    queryFn: () => getPeriodos().then((r) => r.data?.results ?? r.data ?? []),
  })
  const { data: activos } = useQuery({
    queryKey: ['periodos-activos'],
    queryFn: () => getPeriodosActivos().then((r) => r.data),
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

  // Preselecciona el periodo activo de cada recurso en cuanto se carga.
  useEffect(() => {
    if (activos?.cartas && !periodoCartas) setPeriodoCartas(String(activos.cartas.id))
    if (activos?.requisitos && !periodoRequisitos) setPeriodoRequisitos(String(activos.requisitos.id))
    if (activos?.autoevaluacion && !periodoAE) setPeriodoAE(String(activos.autoevaluacion.id))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activos])

  const { data: cumplLicCartas, isLoading: loadCumplLicCartas } = useQuery({
    queryKey: ['cumpl-lic', 'cartas', periodoCartas],
    queryFn: () => getCumplimientoLicenciatura({ periodo: periodoCartas }).then((r) => r.data),
    enabled: !!periodoCartas,
  })
  const { data: cumplDeptoCartas, isLoading: loadCumplDeptoCartas } = useQuery({
    queryKey: ['cumpl-depto', 'cartas', periodoCartas],
    queryFn: () => getCumplimiento({ periodo: periodoCartas }).then((r) => r.data),
    enabled: !!periodoCartas,
  })

  const { data: cumplLicReq, isLoading: loadCumplLicReq } = useQuery({
    queryKey: ['cumpl-lic', 'requisitos', periodoRequisitos],
    queryFn: () => getCumplimientoLicenciatura({ periodo: periodoRequisitos }).then((r) => r.data),
    enabled: !!periodoRequisitos,
  })
  const { data: cumplDeptoReq, isLoading: loadCumplDeptoReq } = useQuery({
    queryKey: ['cumpl-depto', 'requisitos', periodoRequisitos],
    queryFn: () => getCumplimiento({ periodo: periodoRequisitos }).then((r) => r.data),
    enabled: !!periodoRequisitos,
  })

  const { data: resumenAE, isLoading: loadAE } = useQuery({
    queryKey: ['resumen-ae', periodoAE],
    queryFn: () => getResumenAutoevaluacion({ periodo: periodoAE }).then((r) => r.data),
    enabled: !!periodoAE,
  })

  const licenciaturasCartas = cumplLicCartas?.por_licenciatura ?? []
  const licenciaturasReq = cumplLicReq?.por_licenciatura ?? []
  const departamentosCartas = cumplDeptoCartas?.por_departamento ?? []
  const departamentosReq = cumplDeptoReq?.por_departamento ?? []
  const formularios = resumenAE?.formularios ?? []

  async function descargarCartas() {
    setDownloadErrorCartas(null)
    setDownloadingCartas(true)
    try {
      const params = { page_size: 200, periodo: periodoCartas }
      if (filtroLicCartas) params.uea__licenciatura = filtroLicCartas
      if (filtroDeptoCartas) params.profesor__departamento = filtroDeptoCartas

      const res = await getCartas(params)
      const cartas = res.data?.results ?? res.data ?? []

      const wb = XLSX.utils.book_new()
      const ws = XLSX.utils.json_to_sheet(cartas.map((r) => rowToExcel(r, 'cartas')))
      XLSX.utils.book_append_sheet(wb, ws, 'Cartas Temáticas')

      const claveP = periodos.find((p) => String(p.id) === String(periodoCartas))?.clave ?? periodoCartas
      const fecha = new Date().toISOString().slice(0, 10)
      XLSX.writeFile(wb, `cartas_tematicas_${claveP}_${fecha}.xlsx`)
    } catch (e) {
      setDownloadErrorCartas(e?.response?.data?.detail || e?.message || 'No se pudo generar el Excel.')
    } finally {
      setDownloadingCartas(false)
    }
  }

  async function descargarRequisitos() {
    setDownloadErrorReq(null)
    setDownloadingReq(true)
    try {
      const params = { page_size: 200, periodo: periodoRequisitos }
      if (filtroLicReq) params.uea__licenciatura = filtroLicReq
      if (filtroDeptoReq) params.profesor__departamento = filtroDeptoReq

      const res = await getRequisitos(params)
      const reqs = res.data?.results ?? res.data ?? []

      const wb = XLSX.utils.book_new()
      const ws = XLSX.utils.json_to_sheet(reqs.map((r) => rowToExcel(r, 'requisitos')))
      XLSX.utils.book_append_sheet(wb, ws, 'Requisitos')

      const claveP = periodos.find((p) => String(p.id) === String(periodoRequisitos))?.clave ?? periodoRequisitos
      const fecha = new Date().toISOString().slice(0, 10)
      XLSX.writeFile(wb, `requisitos_recuperacion_${claveP}_${fecha}.xlsx`)
    } catch (e) {
      setDownloadErrorReq(e?.response?.data?.detail || e?.message || 'No se pudo generar el Excel.')
    } finally {
      setDownloadingReq(false)
    }
  }

  async function descargarExcelAutoevaluaciones() {
    setDownloadErrorAE(null)
    setDownloadingAE(true)
    try {
      const params = { periodo: periodoAE }
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

      const claveP = periodos.find((p) => String(p.id) === String(periodoAE))?.clave ?? periodoAE
      const fecha = new Date().toISOString().slice(0, 10)
      XLSX.writeFile(wb, `autoevaluaciones_${claveP}_${fecha}.xlsx`)
    } catch (e) {
      setDownloadErrorAE(e?.response?.data?.detail || e?.message || 'No se pudo generar el Excel.')
    } finally {
      setDownloadingAE(false)
    }
  }

  return (
    <div className="p-6 space-y-10">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Reportes</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Indicadores de cumplimiento y autoevaluación.
        </p>
      </div>

      {/* ── Cartas Temáticas ─────────────────────────────────── */}
      <div className="space-y-4">
        <SectionTitle right={<PeriodoSelect periodos={periodos} value={periodoCartas} onChange={setPeriodoCartas} />}>
          Cartas Temáticas
        </SectionTitle>

        {!periodoCartas ? (
          <p className="text-sm text-slate-400 italic">Selecciona un periodo para ver los indicadores.</p>
        ) : (
          <>
            <div>
              <h3 className="text-sm font-medium text-slate-700 mb-2">Cumplimiento por licenciatura</h3>
              {loadCumplLicCartas ? (
                <Loading />
              ) : (
                <div className="rounded-xl border border-slate-200 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                      <tr>
                        <th className="px-4 py-3 text-left">Licenciatura</th>
                        <th className="px-4 py-3 text-left w-48">Cartas Temáticas</th>
                        <th className="px-4 py-3 text-right w-28">UEAs activas</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {licenciaturasCartas.length === 0 && (
                        <tr>
                          <td colSpan={3} className="px-4 py-8 text-center text-slate-400 text-sm">
                            Sin datos de cumplimiento para este periodo.
                          </td>
                        </tr>
                      )}
                      {licenciaturasCartas.map((row) => {
                        const totalUEA = row.total_ueas_activas ?? 0
                        const cartasPub = row.cartas_tematicas?.publicado ?? 0
                        const pctCarta = totalUEA > 0 ? (cartasPub / totalUEA) * 100 : 0
                        return (
                          <tr key={row.licenciatura_id} className="hover:bg-slate-50">
                            <td className="px-4 py-3 font-medium text-slate-800">
                              {row.nombre}
                              <span className="ml-2 text-xs text-slate-400">{row.clave}</span>
                            </td>
                            <td className="px-4 py-3">
                              <PctBar value={pctCarta} color="indigo" />
                              <p className="text-xs text-slate-400 mt-0.5">{cartasPub}/{totalUEA} UEAs</p>
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

            <div>
              <h3 className="text-sm font-medium text-slate-700 mb-2">Cumplimiento por departamento</h3>
              {loadCumplDeptoCartas ? (
                <Loading />
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-200">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                      <tr>
                        <th className="px-4 py-3 text-left">Departamento</th>
                        <th className="px-4 py-3 text-right">Profesores</th>
                        <th className="px-4 py-3 text-right">Carta</th>
                        <th className="px-4 py-3 text-right w-32">% Carta</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {departamentosCartas.length === 0 && (
                        <tr>
                          <td colSpan={4} className="px-4 py-8 text-center text-slate-400 text-sm">
                            Sin datos de cumplimiento para este periodo.
                          </td>
                        </tr>
                      )}
                      {departamentosCartas.map((d) => (
                        <tr key={d.departamento_id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-medium text-slate-800">
                            <span className="text-xs text-slate-400 mr-1">{d.clave}</span>
                            {d.nombre}
                          </td>
                          <td className="px-4 py-3 text-right text-slate-600">{d.total_profesores}</td>
                          <td className="px-4 py-3 text-right text-slate-600">{d.con_carta_publicada}</td>
                          <td className="px-4 py-3 text-right"><PctBar value={d.pct_carta} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h3 className="mb-1 text-sm font-semibold text-slate-700">Descargar Excel</h3>
              <p className="mb-4 text-xs text-slate-500">
                Genera un Excel con todas las cartas temáticas del periodo seleccionado. Filtra
                opcionalmente por licenciatura de la UEA o por departamento del profesor.
              </p>
              {downloadErrorCartas && (
                <Alert type="error" onClose={() => setDownloadErrorCartas(null)}>{downloadErrorCartas}</Alert>
              )}
              <div className="flex flex-wrap items-end gap-3">
                <div className="min-w-[220px]">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Licenciatura (de la UEA)</label>
                  <select value={filtroLicCartas} onChange={(e) => setFiltroLicCartas(e.target.value)} className={inputCls}>
                    <option value="">— Todas —</option>
                    {lics.map((l) => <option key={l.id} value={l.id}>{l.nombre}</option>)}
                  </select>
                </div>
                <div className="min-w-[220px]">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Departamento (del profesor)</label>
                  <select value={filtroDeptoCartas} onChange={(e) => setFiltroDeptoCartas(e.target.value)} className={inputCls}>
                    <option value="">— Todos —</option>
                    {deptos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
                  </select>
                </div>
                <Button onClick={descargarCartas} loading={downloadingCartas}>Descargar Excel</Button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ── Requisitos de Recuperación ───────────────────────── */}
      <div className="space-y-4">
        <SectionTitle right={<PeriodoSelect periodos={periodos} value={periodoRequisitos} onChange={setPeriodoRequisitos} />}>
          Requisitos de Recuperación
        </SectionTitle>

        {!periodoRequisitos ? (
          <p className="text-sm text-slate-400 italic">Selecciona un periodo para ver los indicadores.</p>
        ) : (
          <>
            <div>
              <h3 className="text-sm font-medium text-slate-700 mb-2">Cumplimiento por licenciatura</h3>
              {loadCumplLicReq ? (
                <Loading />
              ) : (
                <div className="rounded-xl border border-slate-200 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                      <tr>
                        <th className="px-4 py-3 text-left">Licenciatura</th>
                        <th className="px-4 py-3 text-left w-48">Req. Recuperación</th>
                        <th className="px-4 py-3 text-right w-28">UEAs activas</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {licenciaturasReq.length === 0 && (
                        <tr>
                          <td colSpan={3} className="px-4 py-8 text-center text-slate-400 text-sm">
                            Sin datos de cumplimiento para este periodo.
                          </td>
                        </tr>
                      )}
                      {licenciaturasReq.map((row) => {
                        const totalUEA = row.total_ueas_activas ?? 0
                        const reqPub = row.requisitos_recuperacion?.publicado ?? 0
                        const pctReq = totalUEA > 0 ? (reqPub / totalUEA) * 100 : 0
                        return (
                          <tr key={row.licenciatura_id} className="hover:bg-slate-50">
                            <td className="px-4 py-3 font-medium text-slate-800">
                              {row.nombre}
                              <span className="ml-2 text-xs text-slate-400">{row.clave}</span>
                            </td>
                            <td className="px-4 py-3">
                              <PctBar value={pctReq} color="emerald" />
                              <p className="text-xs text-slate-400 mt-0.5">{reqPub}/{totalUEA} UEAs</p>
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

            <div>
              <h3 className="text-sm font-medium text-slate-700 mb-2">Cumplimiento por departamento</h3>
              {loadCumplDeptoReq ? (
                <Loading />
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-200">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                      <tr>
                        <th className="px-4 py-3 text-left">Departamento</th>
                        <th className="px-4 py-3 text-right">Profesores</th>
                        <th className="px-4 py-3 text-right">Requisito</th>
                        <th className="px-4 py-3 text-right w-32">% Req.</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {departamentosReq.length === 0 && (
                        <tr>
                          <td colSpan={4} className="px-4 py-8 text-center text-slate-400 text-sm">
                            Sin datos de cumplimiento para este periodo.
                          </td>
                        </tr>
                      )}
                      {departamentosReq.map((d) => (
                        <tr key={d.departamento_id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-medium text-slate-800">
                            <span className="text-xs text-slate-400 mr-1">{d.clave}</span>
                            {d.nombre}
                          </td>
                          <td className="px-4 py-3 text-right text-slate-600">{d.total_profesores}</td>
                          <td className="px-4 py-3 text-right text-slate-600">{d.con_requisito_publicado}</td>
                          <td className="px-4 py-3 text-right"><PctBar value={d.pct_requisito} color="emerald" /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h3 className="mb-1 text-sm font-semibold text-slate-700">Descargar Excel</h3>
              <p className="mb-4 text-xs text-slate-500">
                Genera un Excel con todos los requisitos de recuperación del periodo seleccionado.
                Filtra opcionalmente por licenciatura de la UEA o por departamento del profesor.
              </p>
              {downloadErrorReq && (
                <Alert type="error" onClose={() => setDownloadErrorReq(null)}>{downloadErrorReq}</Alert>
              )}
              <div className="flex flex-wrap items-end gap-3">
                <div className="min-w-[220px]">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Licenciatura (de la UEA)</label>
                  <select value={filtroLicReq} onChange={(e) => setFiltroLicReq(e.target.value)} className={inputCls}>
                    <option value="">— Todas —</option>
                    {lics.map((l) => <option key={l.id} value={l.id}>{l.nombre}</option>)}
                  </select>
                </div>
                <div className="min-w-[220px]">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Departamento (del profesor)</label>
                  <select value={filtroDeptoReq} onChange={(e) => setFiltroDeptoReq(e.target.value)} className={inputCls}>
                    <option value="">— Todos —</option>
                    {deptos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
                  </select>
                </div>
                <Button onClick={descargarRequisitos} loading={downloadingReq}>Descargar Excel</Button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ── Autoevaluación ───────────────────────────────────── */}
      <div className="space-y-4">
        <SectionTitle right={<PeriodoSelect periodos={periodos} value={periodoAE} onChange={setPeriodoAE} />}>
          Autoevaluación
        </SectionTitle>

        {!periodoAE ? (
          <p className="text-sm text-slate-400 italic">Selecciona un periodo para ver los indicadores.</p>
        ) : (
          <>
            {loadAE ? (
              <Loading />
            ) : (
              <div className="space-y-4">
                {formularios.length === 0 && (
                  <p className="text-sm text-slate-400 italic">
                    Sin formularios en este periodo.
                  </p>
                )}
                {formularios.map((f) => {
                  const pct =
                    f.total_profesores > 0
                      ? ((f.respuestas_enviadas / f.total_profesores) * 100).toFixed(0)
                      : null

                  return (
                    <div key={f.formulario_id} className="rounded-xl border border-slate-200 bg-white p-5">
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
                          <p className="text-2xl font-bold text-indigo-600">{f.respuestas_enviadas}</p>
                          <p className="text-xs text-slate-500">Respuestas enviadas</p>
                        </div>
                        <div>
                          <p className="text-2xl font-bold text-slate-700">{f.total_profesores}</p>
                          <p className="text-xs text-slate-500">Profesores activos</p>
                        </div>
                        <div>
                          <p className="text-2xl font-bold text-emerald-600">{pct != null ? `${pct}%` : '—'}</p>
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

            <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h3 className="mb-1 text-sm font-semibold text-slate-700">Descargar puntuaciones</h3>
              <p className="mb-4 text-xs text-slate-500">
                Genera un Excel con la puntuación de autoevaluación de cada profesor activo en
                el periodo (0% si aún no la contesta), su número económico y su departamento.
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
                <Button onClick={descargarExcelAutoevaluaciones} loading={downloadingAE}>Descargar Excel</Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
