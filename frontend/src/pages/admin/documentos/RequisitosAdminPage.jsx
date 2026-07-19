/**
 * Vista de Requisitos de Recuperación para Admin — lectura + filtros.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getRequisitos } from '../../../api/documentos'
import { getPeriodos } from '../../../api/catalogos'
import Table from '../../../components/ui/Table'
import { inputCls } from '../../../components/ui/FormField'

export default function RequisitosAdminPage() {
  const [filtroPeriodo, setFiltroPeriodo] = useState('')

  const params = { estado: 'PUBLICADO' }
  if (filtroPeriodo) params.periodo = filtroPeriodo

  const { data, isLoading } = useQuery({
    queryKey: ['requisitos-admin', 'PUBLICADO', filtroPeriodo],
    queryFn: () => getRequisitos(params).then((r) => r.data?.results ?? r.data ?? []),
  })
  const { data: periodos = [] } = useQuery({
    queryKey: ['periodos'],
    queryFn: () => getPeriodos().then((r) => r.data?.results ?? r.data ?? []),
  })

  const columns = [
    {
      key: 'profesor_nombre', label: 'Profesor',
      render: (v) => <span className="font-medium">{v}</span>,
    },
    {
      key: 'profesor_economico', label: 'Económico', className: 'w-24',
      render: (v) => v ?? <span className="text-slate-400">—</span>,
    },
    {
      key: 'uea_nombre', label: 'UEA',
      render: (v, row) => <div><p>{v}</p><p className="text-xs text-slate-400">{row.periodo_clave}</p></div>,
    },
    {
      key: 'nombre_grupo', label: 'Grupo',
      render: (v, row) => <div><p>{v}</p><p className="text-xs text-slate-400">ID: {row.id_grupo}</p></div>,
    },
    {
      key: 'licenciatura_nombre', label: 'Programa',
      render: (_, row) => row.licenciatura_nombre ?? row.posgrado_nombre ?? <span className="text-slate-400">—</span>,
    },
    {
      key: 'departamento_nombre', label: 'Departamento',
      render: (v) => v ?? <span className="text-slate-400">—</span>,
    },
    {
      key: 'fecha_hora', label: 'Fecha / hora',
      render: (v) => v || <span className="text-slate-400">—</span>,
    },
    {
      key: 'enlace', label: 'Enlace', className: 'w-28',
      render: (_, row) => (
        <a
          href={`/publico/requisitos/${row.id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-600 underline hover:text-indigo-700"
        >
          Ver público
        </a>
      ),
    },
    {
      key: 'updated_at', label: 'Actualizado', className: 'w-32',
      render: (v) => new Date(v).toLocaleDateString('es-MX'),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Requisitos de Recuperación</h1>
        <p className="text-sm text-slate-500 mt-0.5">Vista global de documentos publicados.</p>
      </div>

      <div className="flex gap-4 flex-wrap">
        <select value={filtroPeriodo} onChange={(e) => setFiltroPeriodo(e.target.value)} className={inputCls + ' w-36'}>
          <option value="">Todos los periodos</option>
          {periodos.map((p) => <option key={p.id} value={p.id}>{p.clave}</option>)}
        </select>
      </div>

      <Table columns={columns} data={data ?? []} loading={isLoading} emptyText="Sin documentos publicados para el periodo seleccionado" />
    </div>
  )
}
