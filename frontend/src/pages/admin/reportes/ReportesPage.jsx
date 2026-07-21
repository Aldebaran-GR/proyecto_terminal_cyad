/**
 * Reportes — Admin.
 *
 * Página de descarga de documentos en Excel. El admin elige tipo de
 * documento (Cartas / Requisitos / Autoevaluación), periodo ("Todos los
 * periodos" genera una hoja por periodo con datos) y opcionalmente
 * departamento. No hay filtro de licenciatura — no aplica a autoevaluación,
 * y se buscó un flujo uniforme entre los 3 tipos.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as XLSX from 'xlsx'
import { getAutoevaluacionProfesores } from '../../../api/reportes'
import { getCartas, getRequisitos } from '../../../api/documentos'
import { getPeriodos, getDepartamentos } from '../../../api/catalogos'
import Alert from '../../../components/ui/Alert'
import Button from '../../../components/ui/Button'
import { inputCls } from '../../../components/ui/FormField'
import { parseApiError } from '../../../utils/apiError'

const TIPOS = [
  { value: 'cartas', label: 'Cartas Temáticas' },
  { value: 'requisitos', label: 'Requisitos de Recuperación' },
  { value: 'autoevaluacion', label: 'Autoevaluación' },
]

// Mapea una fila de documento (Carta o Requisito) a las columnas del Excel.
// El enlace solo se llena para documentos PUBLICADO — solo se descargan
// documentos publicados, así que siempre queda lleno.
function rowToExcel(row, publicPath) {
  return {
    Profesor: row.profesor_nombre ?? '',
    Económico: row.profesor_economico ?? '',
    UEA: row.uea_nombre ?? '',
    Grupo: row.nombre_grupo ?? '',
    Actualizada: row.updated_at ? new Date(row.updated_at).toLocaleDateString('es-MX') : '',
    Enlace: `${window.location.origin}/publico/${publicPath}/${row.id}`,
    Licenciatura: row.licenciatura_nombre ?? row.posgrado_nombre ?? '',
    Departamento: row.departamento_nombre ?? '',
  }
}

function rowAutoevaluacionExcel(p) {
  return {
    Profesor: p.nombre_completo ?? '',
    Económico: p.numero_economico ?? '',
    Departamento: p.departamento_nombre ?? '',
    'Puntuación (%)': p.porcentaje ?? 0,
  }
}

// El nombre de hoja de Excel no admite más de 31 caracteres ni : \ / ? * [ ]
function sheetName(clave) {
  return String(clave).replace(/[:\\/?*[\]]/g, '-').slice(0, 31)
}

export default function ReportesPage() {
  const [tipo, setTipo] = useState('cartas')
  const [periodoId, setPeriodoId] = useState('')
  const [deptoId, setDeptoId] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState(null)

  const { data: periodos = [] } = useQuery({
    queryKey: ['periodos'],
    queryFn: () => getPeriodos().then((r) => r.data?.results ?? r.data ?? []),
  })
  const { data: deptos = [] } = useQuery({
    queryKey: ['departamentos'],
    queryFn: () => getDepartamentos().then((r) => r.data?.results ?? r.data ?? []),
    staleTime: 5 * 60_000,
  })

  async function descargarDocumento(publicPath, fetcher) {
    const params = { estado: 'PUBLICADO', page_size: 500 }
    if (periodoId) params.periodo = periodoId
    if (deptoId) params.profesor__departamento = deptoId

    const res = await fetcher(params)
    const rows = res.data?.results ?? res.data ?? []

    const porPeriodo = new Map()
    for (const row of rows) {
      const clave = row.periodo_clave ?? 'Sin periodo'
      if (!porPeriodo.has(clave)) porPeriodo.set(clave, [])
      porPeriodo.get(clave).push(row)
    }

    const wb = XLSX.utils.book_new()
    if (porPeriodo.size === 0) {
      XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([]), 'Sin datos')
    } else {
      for (const [clave, groupRows] of porPeriodo) {
        const ws = XLSX.utils.json_to_sheet(groupRows.map((r) => rowToExcel(r, publicPath)))
        XLSX.utils.book_append_sheet(wb, ws, sheetName(clave))
      }
    }
    return wb
  }

  async function descargarAutoevaluacion() {
    const paramsBase = {}
    if (deptoId) paramsBase.departamento = deptoId

    const periodosADescargar = periodoId
      ? periodos.filter((p) => String(p.id) === String(periodoId))
      : periodos

    const resultados = await Promise.all(
      periodosADescargar.map((p) =>
        getAutoevaluacionProfesores({ ...paramsBase, periodo: p.id }).then((r) => ({
          clave: p.clave,
          formulario: r.data?.formulario ?? null,
          profesores: r.data?.profesores ?? [],
        }))
      )
    )

    // Sin filtro de periodo, se omiten los periodos que nunca tuvieron
    // autoevaluación (formulario null) para no generar hojas vacías.
    const conDatos = periodoId ? resultados : resultados.filter((r) => r.formulario)

    const wb = XLSX.utils.book_new()
    if (conDatos.length === 0) {
      XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([]), 'Sin datos')
    } else {
      for (const { clave, profesores } of conDatos) {
        const ws = XLSX.utils.json_to_sheet(profesores.map(rowAutoevaluacionExcel))
        XLSX.utils.book_append_sheet(wb, ws, sheetName(clave))
      }
    }
    return wb
  }

  async function descargar() {
    setDownloadError(null)
    setDownloading(true)
    try {
      let wb
      let nombreTipo
      if (tipo === 'cartas') {
        wb = await descargarDocumento('cartas', getCartas)
        nombreTipo = 'cartas_tematicas'
      } else if (tipo === 'requisitos') {
        wb = await descargarDocumento('requisitos', getRequisitos)
        nombreTipo = 'requisitos_recuperacion'
      } else {
        wb = await descargarAutoevaluacion()
        nombreTipo = 'autoevaluaciones'
      }

      const clavePeriodo = periodoId
        ? periodos.find((p) => String(p.id) === String(periodoId))?.clave ?? periodoId
        : 'todos'
      const fecha = new Date().toISOString().slice(0, 10)
      XLSX.writeFile(wb, `${nombreTipo}_${clavePeriodo}_${fecha}.xlsx`)
    } catch (e) {
      setDownloadError(parseApiError(e?.response?.data, e?.message || 'No se pudo generar el Excel.'))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Reportes</h1>
        <p className="text-sm text-slate-500 mt-0.5">Descarga de documentos.</p>
      </div>

      <div className="max-w-2xl rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h2 className="mb-1 text-sm font-semibold text-slate-700">Descargar Excel</h2>
        <p className="mb-4 text-xs text-slate-500">
          Genera un Excel con los documentos publicados del tipo seleccionado. Si eliges
          "Todos los periodos", el archivo tendrá una hoja por cada periodo con datos.
          Filtra opcionalmente por departamento del profesor.
        </p>
        {downloadError && (
          <Alert type="error" onClose={() => setDownloadError(null)}>{downloadError}</Alert>
        )}
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Tipo de documento</label>
            <select value={tipo} onChange={(e) => setTipo(e.target.value)} className={inputCls}>
              {TIPOS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Periodo</label>
            <select value={periodoId} onChange={(e) => setPeriodoId(e.target.value)} className={inputCls}>
              <option value="">Todos los periodos</option>
              {periodos.map((p) => <option key={p.id} value={p.id}>{p.clave}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Departamento</label>
            <select value={deptoId} onChange={(e) => setDeptoId(e.target.value)} className={inputCls}>
              <option value="">— Todos —</option>
              {deptos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
            </select>
          </div>
          <Button onClick={descargar} loading={downloading}>Descargar Excel</Button>
        </div>
      </div>
    </div>
  )
}
