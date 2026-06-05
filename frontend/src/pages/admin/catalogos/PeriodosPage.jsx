/**
 * Catálogo de Periodos — Admin.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getPeriodos, createPeriodo, updatePeriodo, deletePeriodo,
} from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Modal from '../../../components/ui/Modal'
import Table from '../../../components/ui/Table'
import Alert from '../../../components/ui/Alert'
import FormField, { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

const empty = () => ({ clave: '', fecha_inicio: '', fecha_fin: '', activo: false, estado: true })

export default function PeriodosPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState(false)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(empty())
  const [apiError, setApiError] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['periodos'],
    queryFn: () => getPeriodos().then((r) => r.data?.results ?? r.data ?? []),
  })

  const openCreate = () => { setSelected(null); setForm(empty()); setModal(true) }
  const openEdit = (row) => {
    setSelected(row)
    setForm({ clave: row.clave, fecha_inicio: row.fecha_inicio, fecha_fin: row.fecha_fin, activo: row.activo, estado: row.estado })
    setModal(true)
  }
  const closeModal = () => { setModal(false); setApiError(null) }

  const saveMut = useMutation({
    mutationFn: (d) => selected ? updatePeriodo(selected.id, d) : createPeriodo(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['periodos'] }); closeModal() },
    onError: (e) => {
      const data = e.response?.data
      setApiError(data?.clave?.[0] || data?.fecha_fin?.[0] || data?.non_field_errors?.[0] || data?.detail || 'Error al guardar.')
    },
  })
  const delMut = useMutation({
    mutationFn: (id) => deletePeriodo(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['periodos'] }),
    onError: () => setApiError('No se puede eliminar este periodo (tiene documentos asociados).'),
  })

  const columns = [
    { key: 'clave', label: 'Clave', className: 'w-24 font-mono' },
    { key: 'fecha_inicio', label: 'Inicio', className: 'w-28' },
    { key: 'fecha_fin', label: 'Fin', className: 'w-28' },
    {
      key: 'activo', label: 'Activo', className: 'w-20',
      render: (v) => v ? <span className="text-emerald-600 font-semibold text-xs">● Activo</span> : <span className="text-slate-400 text-xs">—</span>,
    },
    { key: 'estado', label: 'Estado', className: 'w-24', render: (v) => <Badge label={v ? 'ACTIVO' : 'INACTIVO'} variant={v ? 'ACTIVO' : 'INACTIVO'} /> },
    {
      key: 'actions', label: '', className: 'w-32 text-right',
      render: (_, row) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>Editar</Button>
          <Button size="sm" variant="danger" onClick={() => window.confirm('¿Eliminar este periodo?') && delMut.mutate(row.id)}>Eliminar</Button>
        </div>
      ),
    },
  ]

  const f = (key) => (e) => setForm((p) => ({ ...p, [key]: e.target.value }))

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-900">Periodos</h1>
        <Button onClick={openCreate}>+ Nuevo</Button>
      </div>
      {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}
      <Table columns={columns} data={data ?? []} loading={isLoading} emptyText="Sin periodos" />

      <Modal open={modal} onClose={closeModal} title={selected ? 'Editar Periodo' : 'Nuevo Periodo'}
        footer={<>
          <Button variant="secondary" onClick={closeModal}>Cancelar</Button>
          <Button loading={saveMut.isPending} onClick={() => saveMut.mutate(form)}>Guardar</Button>
        </>}>
        {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}
        <div className="space-y-4">
          <FormField label="Clave" required hint="Formato: YY-I / YY-P / YY-O">
            <input value={form.clave} onChange={f('clave')} className={inputCls} placeholder="ej. 26-I" />
          </FormField>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Fecha de inicio" required>
              <input type="date" value={form.fecha_inicio} onChange={f('fecha_inicio')} className={inputCls} />
            </FormField>
            <FormField label="Fecha de fin" required>
              <input type="date" value={form.fecha_fin} onChange={f('fecha_fin')} className={inputCls} />
            </FormField>
          </div>
          <div className="flex gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.activo} onChange={(e) => setForm((p) => ({ ...p, activo: e.target.checked }))} className="h-4 w-4 accent-indigo-600" />
              <span className="text-sm text-slate-700">Periodo activo</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.estado} onChange={(e) => setForm((p) => ({ ...p, estado: e.target.checked }))} className="h-4 w-4 accent-indigo-600" />
              <span className="text-sm text-slate-700">Habilitado</span>
            </label>
          </div>
          <p className="text-xs text-slate-400">Solo puede haber un periodo marcado como "activo" a la vez.</p>
        </div>
      </Modal>
    </div>
  )
}
