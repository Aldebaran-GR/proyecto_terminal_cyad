/**
 * Catálogo de Áreas — Admin.
 * Patrón: Tabla + Modal CRUD. Cada Área tiene (nombre, descripción) y se
 * vincula a las UEAs vía FK opcional. La unicidad es por (nombre, descripcion).
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAreas, createArea, updateArea, deleteArea,
} from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Modal from '../../../components/ui/Modal'
import Table from '../../../components/ui/Table'
import Alert from '../../../components/ui/Alert'
import FormField, { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

const empty = () => ({ nombre: '', descripcion: '', estado: true })

export default function AreasPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState(false)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(empty())
  const [apiError, setApiError] = useState(null)
  const [search, setSearch] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['areas', search],
    queryFn: () =>
      getAreas(search ? { search } : undefined).then((r) => r.data?.results ?? r.data ?? []),
  })

  const openCreate = () => { setSelected(null); setForm(empty()); setModal(true) }
  const openEdit = (row) => {
    setSelected(row)
    setForm({ nombre: row.nombre, descripcion: row.descripcion ?? '', estado: row.estado })
    setModal(true)
  }
  const closeModal = () => { setModal(false); setApiError(null) }

  const saveMut = useMutation({
    mutationFn: (d) => selected ? updateArea(selected.id, d) : createArea(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['areas'] }); closeModal() },
    onError: (e) =>
      setApiError(
        e.response?.data?.nombre?.[0]
        || e.response?.data?.non_field_errors?.[0]
        || e.response?.data?.detail
        || 'Error al guardar.'
      ),
  })
  const delMut = useMutation({
    mutationFn: (id) => deleteArea(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['areas'] }),
    onError: () => setApiError('No se puede eliminar esta área (tiene UEAs asociadas).'),
  })

  const columns = [
    { key: 'nombre', label: 'Nombre' },
    { key: 'descripcion', label: 'Descripción', render: (v) => v || <span className="text-slate-400">—</span> },
    { key: 'estado', label: 'Estado', className: 'w-24', render: (v) => <Badge label={v ? 'ACTIVO' : 'INACTIVO'} variant={v ? 'ACTIVO' : 'INACTIVO'} /> },
    {
      key: 'actions', label: '', className: 'w-32 text-right',
      render: (_, row) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>Editar</Button>
          <Button size="sm" variant="danger" loading={delMut.isPending}
            onClick={() => window.confirm('¿Eliminar esta área?') && delMut.mutate(row.id)}>
            Eliminar
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-900">Áreas</h1>
        <Button onClick={openCreate}>+ Nueva Área</Button>
      </div>
      {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}

      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Buscar por nombre o descripción…"
        className={inputCls + ' max-w-sm'}
      />

      <Table columns={columns} data={data ?? []} loading={isLoading} emptyText="Sin áreas registradas" />

      <Modal open={modal} onClose={closeModal} title={selected ? 'Editar Área' : 'Nueva Área'}
        footer={<>
          <Button variant="secondary" onClick={closeModal}>Cancelar</Button>
          <Button loading={saveMut.isPending} onClick={() => saveMut.mutate(form)}>Guardar</Button>
        </>}>
        {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}
        <div className="space-y-4">
          <FormField label="Nombre" required>
            <input
              value={form.nombre}
              onChange={(e) => setForm((p) => ({ ...p, nombre: e.target.value }))}
              className={inputCls}
              placeholder="ej. Optativas de interés profesional"
            />
          </FormField>
          <FormField label="Descripción" hint="Sirve para distinguir áreas con el mismo nombre">
            <input
              value={form.descripcion}
              onChange={(e) => setForm((p) => ({ ...p, descripcion: e.target.value }))}
              className={inputCls}
              placeholder="ej. Área de concentración: Tipografía"
            />
          </FormField>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.estado}
              onChange={(e) => setForm((p) => ({ ...p, estado: e.target.checked }))}
              className="h-4 w-4 accent-indigo-600"
            />
            <span className="text-sm text-slate-700">Activa</span>
          </label>
        </div>
      </Modal>
    </div>
  )
}
