/**
 * Lista de Formularios de Autoevaluación — Admin.
 *
 * Acciones por fila (mismo patrón que documentos del profesor):
 *   • Ver      → vista previa de cómo lucirá para el profesor.
 *   • Editar   → si está PUBLICADO, despublica primero y abre el builder.
 *   • Eliminar → si está PUBLICADO, despublica primero y elimina.
 */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getFormularios,
  createFormulario,
  deleteFormulario,
  despublicarFormulario,
} from '../../../api/autoevaluacion'
import { getPeriodos } from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Badge from '../../../components/ui/Badge'
import Table from '../../../components/ui/Table'
import Alert from '../../../components/ui/Alert'
import Modal from '../../../components/ui/Modal'
import FormField, { inputCls } from '../../../components/ui/FormField'

export default function AutoevaluacionAdminPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [apiError, setApiError] = useState(null)
  const [createModal, setCreateModal] = useState(false)
  const [newForm, setNewForm] = useState({ titulo: '', descripcion: '', periodo: '' })

  // Polling cada 15 s para reflejar respuestas que profesores envían en vivo,
  // sin obligar al admin a recargar.
  const { data, isLoading } = useQuery({
    queryKey: ['formularios'],
    queryFn: () => getFormularios().then((r) => r.data?.results ?? r.data ?? []),
    refetchInterval: 15_000,
  })
  const { data: periodos = [] } = useQuery({
    queryKey: ['periodos'],
    queryFn: () => getPeriodos().then((r) => r.data?.results ?? r.data ?? []),
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: ['formularios'] })

  const createMut = useMutation({
    mutationFn: (d) => createFormulario(d),
    onSuccess: (r) => {
      invalidate()
      setCreateModal(false)
      // Llevar directo al builder para empezar a editar
      if (r?.data?.id) navigate(`/admin/autoevaluacion/${r.data.id}`)
    },
    onError: (e) => setApiError(e.response?.data?.detail || 'Error al crear el formulario.'),
  })

  // Considera tanto PUBLICADO como CERRADO como "no editable directo";
  // ambos necesitan despublicarse para volver a BORRADOR.
  const needsDespublicar = (row) =>
    row.estado === 'PUBLICADO' || row.estado === 'CERRADO'

  const editMut = useMutation({
    mutationFn: async (row) => {
      if (needsDespublicar(row)) {
        await despublicarFormulario(row.id)
      }
      return row.id
    },
    onSuccess: (id) => {
      invalidate()
      navigate(`/admin/autoevaluacion/${id}`)
    },
    onError: (e) => setApiError(e.response?.data?.detail || 'No se pudo abrir el editor.'),
  })

  const deleteMut = useMutation({
    mutationFn: async (row) => {
      if (needsDespublicar(row)) {
        await despublicarFormulario(row.id)
      }
      return deleteFormulario(row.id)
    },
    onSuccess: invalidate,
    onError: (e) => setApiError(
      e.response?.data?.detail
      || e.response?.data?.non_field_errors?.[0]
      || 'No se pudo eliminar el formulario.'
    ),
  })

  const onEditClick = (row) => {
    if (needsDespublicar(row)) {
      if (!window.confirm(
        `Este formulario está ${row.estado}. Para editarlo se cerrará primero ` +
        '(dejará de aparecer para los profesores). ¿Continuar?'
      )) return
    }
    editMut.mutate(row)
  }

  const onDeleteClick = (row) => {
    const total = row.total_respuestas ?? 0
    let aviso
    if (needsDespublicar(row) && total > 0) {
      aviso = `Este formulario está ${row.estado} y tiene ${total} respuesta(s). Se cerrará, el historial se borrará y se eliminará. ¿Continuar?`
    } else if (needsDespublicar(row)) {
      aviso = `Este formulario está ${row.estado}. Se cerrará y eliminará. ¿Continuar?`
    } else if (total > 0) {
      aviso = `Este formulario tiene ${total} respuesta(s). Si lo eliminas, se borrará el historial. ¿Continuar?`
    } else {
      aviso = '¿Eliminar este formulario?'
    }
    if (window.confirm(aviso)) deleteMut.mutate(row)
  }

  const columns = [
    {
      key: 'titulo', label: 'Formulario',
      render: (v, row) => (
        <div>
          <p className="font-medium text-slate-800">{v}</p>
          <p className="text-xs text-slate-400">{row.periodo_clave}</p>
        </div>
      ),
    },
    {
      key: 'estado', label: 'Estado', className: 'w-28',
      render: (v) => <Badge label={v} variant={v} />,
    },
    { key: 'total_preguntas', label: 'Preguntas', className: 'w-24 text-center' },
    { key: 'total_respuestas', label: 'Respuestas', className: 'w-24 text-center' },
    {
      key: 'actions', label: '', className: 'w-64 text-right',
      render: (_, row) => (
        <div className="flex justify-end gap-2">
          <Link to={`/admin/autoevaluacion/${row.id}/preview`}>
            <Button size="sm" variant="secondary">Ver</Button>
          </Link>
          <Button
            size="sm"
            variant="secondary"
            loading={editMut.isPending && editMut.variables?.id === row.id}
            onClick={() => onEditClick(row)}
          >
            Editar
          </Button>
          <Button
            size="sm"
            variant="danger"
            loading={deleteMut.isPending && deleteMut.variables?.id === row.id}
            onClick={() => onDeleteClick(row)}
          >
            Eliminar
          </Button>
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
          <Button
            loading={createMut.isPending}
            onClick={() => createMut.mutate({
              titulo: newForm.titulo,
              descripcion: newForm.descripcion,
              periodo: Number(newForm.periodo),
            })}
          >
            Crear borrador
          </Button>
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
          <p className="text-xs text-slate-400">
            Después de crearlo entrarás al editor de preguntas. Cuando esté listo, lo podrás publicar.
          </p>
        </div>
      </Modal>
    </div>
  )
}
