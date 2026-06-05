/**
 * Catálogo de Departamentos — Admin.
 * Patrón: Tabla + Modal CRUD.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getDepartamentos, createDepartamento, updateDepartamento, deleteDepartamento,
} from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Modal from '../../../components/ui/Modal'
import Table from '../../../components/ui/Table'
import Alert from '../../../components/ui/Alert'
import FormField, { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

const empty = () => ({ clave: '', nombre: '', estado: true })

export default function DepartamentosPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState(false)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(empty())
  const [apiError, setApiError] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['departamentos'],
    queryFn: () => getDepartamentos().then((r) => r.data?.results ?? r.data ?? []),
  })

  const openCreate = () => { setSelected(null); setForm(empty()); setModal(true) }
  const openEdit = (row) => { setSelected(row); setForm({ clave: row.clave, nombre: row.nombre, estado: row.estado }); setModal(true) }
  const closeModal = () => { setModal(false); setApiError(null) }

  const saveMut = useMutation({
    mutationFn: (d) => selected ? updateDepartamento(selected.id, d) : createDepartamento(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['departamentos'] }); closeModal() },
    onError: (e) => setApiError(e.response?.data?.clave?.[0] || e.response?.data?.nombre?.[0] || e.response?.data?.detail || 'Error al guardar.'),
  })
  const delMut = useMutation({
    mutationFn: (id) => deleteDepartamento(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['departamentos'] }),
    onError: (e) => setApiError(e.response?.data?.detail || 'No se puede eliminar (tiene registros asociados).'),
  })

  const columns = [
    { key: 'clave', label: 'Clave', className: 'w-24' },
    { key: 'nombre', label: 'Nombre' },
    { key: 'estado', label: 'Estado', className: 'w-24', render: (v) => <Badge label={v ? 'ACTIVO' : 'INACTIVO'} variant={v ? 'ACTIVO' : 'INACTIVO'} /> },
    {
      key: 'actions', label: '', className: 'w-32 text-right',
      render: (_, row) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>Editar</Button>
          <Button size="sm" variant="danger" loading={delMut.isPending}
            onClick={() => window.confirm('¿Eliminar este departamento?') && delMut.mutate(row.id)}>
            Eliminar
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-900">Departamentos</h1>
        <Button onClick={openCreate}>+ Nuevo</Button>
      </div>
      {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}
      <Table columns={columns} data={data ?? []} loading={isLoading} emptyText="Sin departamentos" />

      <Modal open={modal} onClose={closeModal} title={selected ? 'Editar Departamento' : 'Nuevo Departamento'}
        footer={<>
          <Button variant="secondary" onClick={closeModal}>Cancelar</Button>
          <Button loading={saveMut.isPending} onClick={() => saveMut.mutate(form)}>Guardar</Button>
        </>}>
        {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}
        <div className="space-y-4">
          <FormField label="Clave" required><input value={form.clave} onChange={(e) => setForm((p) => ({ ...p, clave: e.target.value }))} className={inputCls} placeholder="ej. EDT" /></FormField>
          <FormField label="Nombre" required><input value={form.nombre} onChange={(e) => setForm((p) => ({ ...p, nombre: e.target.value }))} className={inputCls} placeholder="Nombre completo del departamento" /></FormField>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.estado} onChange={(e) => setForm((p) => ({ ...p, estado: e.target.checked }))} className="h-4 w-4 accent-indigo-600" />
            <span className="text-sm text-slate-700">Activo</span>
          </label>
        </div>
      </Modal>
    </div>
  )
}
