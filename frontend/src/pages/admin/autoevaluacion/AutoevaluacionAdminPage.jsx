/**
 * Lista de Formularios de Autoevaluación — Admin.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getFormularios, createFormulario, deleteFormulario,
  publicarFormulario, cerrarFormulario, publicarRevisionFormulario,
} from '../../../api/autoevaluacion'
import { getPeriodos } from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Badge from '../../../components/ui/Badge'
import Table from '../../../components/ui/Table'
import Alert from '../../../components/ui/Alert'
import Modal from '../../../components/ui/Modal'
import FormField, { inputCls } from '../../../components/ui/FormField'

const ESTADO_COLORS = { BORRADOR: 'BORRADOR', PUBLICADO: 'PUBLICADO', CERRADO: 'CERRADO' }

export default function AutoevaluacionAdminPage() {
  const qc = useQueryClient()
  const [apiError, setApiError] = useState(null)
  const [createModal, setCreateModal] = useState(false)
  const [newForm, setNewForm] = useState({ titulo: '', descripcion: '', periodo: '' })

  const { data, isLoading } = useQuery({
    queryKey: ['formularios'],
    queryFn: () => getFormularios().then((r) => r.data?.results ?? r.data ?? []),
  })
  const { data: periodos = [] } = useQuery({
    queryKey: ['periodos'],
    queryFn: () => getPeriodos().then((r) => r.data?.results ?? r.data ?? []),
  })

  const createMut = useMutation({
    mutationFn: (d) => createFormulario(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['formularios'] }); setCreateModal(false) },
    onError: (e) => setApiError(e.response?.data?.detail || 'Error al crear el formulario.'),
  })
  const makeMut = (fn, msg) => useMutation({
    mutationFn: (id) => fn(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['formularios'] }),
    onError: (e) => setApiError(e.response?.data?.non_field_errors?.[0] || msg),
  })
  const pubMut = makeMut(publicarFormulario, 'Error al publicar.')
  const cerMut = makeMut(cerrarFormulario, 'Error al cerrar.')
  const revMut = makeMut(publicarRevisionFormulario, 'Error al publicar revisión.')
  const delMut = useMutation({
    mutationFn: (id) => deleteFormulario(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['formularios'] }),
    onError: (e) => setApiError(
      e.response?.data?.detail
      || e.response?.data?.non_field_errors?.[0]
      || 'No se puede eliminar este formulario.'
    ),
  })

  const confirmarYEliminar = (row) => {
    const tieneRespuestas = (row.total_respuestas ?? 0) > 0
    const aviso = tieneRespuestas
      ? `Este formulario tiene ${row.total_respuestas} respuesta(s) registradas. ` +
        `Si lo eliminas, se borrará el historial. ¿Continuar?`
      : '¿Eliminar este formulario?'
    if (window.confirm(aviso)) delMut.mutate(row.id)
  }

  const columns = [
    {
      key: 'titulo', label: 'Formulario',
      render: (v, row) => (
        <div>
          <Link to={`/admin/autoevaluacion/${row.id}`} className="font-medium text-indigo-600 hover:underline">{v}</Link>
          <p className="text-xs text-slate-400">v{row.version} · {row.periodo_clave}</p>
        </div>
      ),
    },
    {
      key: 'estado', label: 'Estado', className: 'w-28',
      render: (v) => <Badge label={v} variant={ESTADO_COLORS[v]} />,
    },
    { key: 'total_preguntas', label: 'Preguntas', className: 'w-24 text-center' },
    { key: 'total_respuestas', label: 'Respuestas', className: 'w-24 text-center' },
    {
      key: 'actions', label: '', className: 'w-72 text-right',
      render: (_, row) => (
        <div className="flex justify-end gap-1.5 flex-wrap">
          <Link to={`/admin/autoevaluacion/${row.id}`}>
            <Button size="sm" variant="secondary">Ver / Editar</Button>
          </Link>
          {row.estado === 'BORRADOR' && (
            <Button size="sm" onClick={() => pubMut.mutate(row.id)} loading={pubMut.isPending}>Publicar</Button>
          )}
          {row.estado === 'PUBLICADO' && (
            <Button size="sm" variant="secondary" onClick={() => cerMut.mutate(row.id)} loading={cerMut.isPending}>Cerrar</Button>
          )}
          {row.estado === 'CERRADO' && (
            <Button size="sm" onClick={() => revMut.mutate(row.id)} loading={revMut.isPending}>Nueva revisión</Button>
          )}
          <Button size="sm" variant="danger" onClick={() => confirmarYEliminar(row)} loading={delMut.isPending}>Eliminar</Button>
        </div>
      ),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Autoevaluación</h1>
          <p className="text-sm text-slate-500 mt-0.5">Formularios de evaluación docente.</p>
        </div>
        <Button onClick={() => { setNewForm({ titulo: '', descripcion: '', periodo: '' }); setCreateModal(true) }}>
          + Nuevo Formulario
        </Button>
      </div>

      {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}
      <Table columns={columns} data={data ?? []} loading={isLoading} emptyText="Sin formularios" />

      <Modal open={createModal} onClose={() => setCreateModal(false)} title="Nuevo Formulario de Autoevaluación"
        footer={<>
          <Button variant="secondary" onClick={() => setCreateModal(false)}>Cancelar</Button>
          <Button loading={createMut.isPending} onClick={() => createMut.mutate({ titulo: newForm.titulo, descripcion: newForm.descripcion, periodo: Number(newForm.periodo) })}>Crear</Button>
        </>}>
        <div className="space-y-4">
          <FormField label="Título" required>
            <input value={newForm.titulo} onChange={(e) => setNewForm((p) => ({ ...p, titulo: e.target.value }))} className={inputCls} placeholder="ej. Autoevaluación Docente 26-I" />
          </FormField>
          <FormField label="Descripción">
            <textarea value={newForm.descripcion} onChange={(e) => setNewForm((p) => ({ ...p, descripcion: e.target.value }))} rows={2} className={inputCls} placeholder="Descripción del formulario" />
          </FormField>
          <FormField label="Periodo" required>
            <select value={newForm.periodo} onChange={(e) => setNewForm((p) => ({ ...p, periodo: e.target.value }))} className={inputCls}>
              <option value="">-- Selecciona --</option>
              {periodos.map((p) => <option key={p.id} value={p.id}>{p.clave}</option>)}
            </select>
          </FormField>
        </div>
      </Modal>
    </div>
  )
}
