/**
 * Vista de Cartas Temáticas para Admin — lectura + filtros.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCartas } from '../../../api/documentos'
import { getPeriodos } from '../../../api/catalogos'
import Table from '../../../components/ui/Table'
import Badge from '../../../components/ui/Badge'
import Loading from '../../../components/ui/Loading'
import { inputCls } from '../../../components/ui/FormField'

export default function CartasAdminPage() {
  const [filtroEstado, setFiltroEstado] = useState('')
  const [filtroPeriodo, setFiltroPeriodo] = useState('')

  const params = {}
  if (filtroEstado) params.estado = filtroEstado
  if (filtroPeriodo) params.periodo = filtroPeriodo

  const { data, isLoading } = useQuery({
    queryKey: ['cartas-admin', filtroEstado, filtroPeriodo],
    queryFn: () => getCartas(params).then((r) => r.data?.results ?? r.data ?? []),
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
      key: 'uea_nombre', label: 'UEA',
      render: (v, row) => <div><p>{v}</p><p className="text-xs text-slate-400">{row.periodo_clave}</p></div>,
    },
    {
      key: 'nombre_grupo', label: 'Grupo',
      render: (v, row) => <div><p>{v}</p><p className="text-xs text-slate-400">ID: {row.id_grupo}</p></div>,
    },
    {
      key: 'modalidad', label: 'Modalidad',
      render: (v) => v || <span className="text-slate-400">—</span>,
    },
    {
      key: 'estado', label: 'Estado', className: 'w-24',
      render: (v) => <Badge label={v} variant={v} />,
    },
    {
      key: 'updated_at', label: 'Actualizada', className: 'w-32',
      render: (v) => new Date(v).toLocaleDateString('es-MX'),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Cartas Temáticas</h1>
          <p className="text-sm text-slate-500 mt-0.5">Vista global de todos los profesores.</p>
        </div>
      </div>

      {/* Filtros */}
      <div className="flex gap-4 flex-wrap">
        <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)} className={inputCls + ' w-44'}>
          <option value="">Todos los estados</option>
          <option value="BORRADOR">Borrador</option>
          <option value="PUBLICADO">Publicado</option>
        </select>
        <select value={filtroPeriodo} onChange={(e) => setFiltroPeriodo(e.target.value)} className={inputCls + ' w-36'}>
          <option value="">Todos los periodos</option>
          {periodos.map((p) => <option key={p.id} value={p.id}>{p.clave}</option>)}
        </select>
      </div>

      <Table columns={columns} data={data ?? []} loading={isLoading} emptyText="Sin cartas con los filtros aplicados" />
    </div>
  )
}
