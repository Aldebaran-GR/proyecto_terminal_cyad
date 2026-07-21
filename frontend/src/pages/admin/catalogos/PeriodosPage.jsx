/**
 * Catálogo de Periodos — Admin.
 *
 * Cada periodo puede estar activo de forma independiente para cada tipo de
 * recurso: Cartas Temáticas, Requisitos de Recuperación y Autoevaluación.
 * El backend garantiza que a lo más un periodo tenga cada flag a la vez,
 * apagando automáticamente el flag en los demás cuando lo prendes aquí.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getPeriodos, createPeriodo, updatePeriodo, deletePeriodo,
  previewEliminacionPeriodo,
} from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Modal from '../../../components/ui/Modal'
import Table from '../../../components/ui/Table'
import Alert from '../../../components/ui/Alert'
import FormField, { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'
import { parseApiError } from '../../../utils/apiError'

const empty = () => ({
  clave: '', fecha_inicio: '', fecha_fin: '',
  activo_cartas: false, activo_requisitos: false, activo_autoevaluacion: false,
  estado: true,
})

/* Chip clicable que prende / apaga un flag por recurso ─────────────────── */
function FlagChip({ label, value, onToggle, busy }) {
  return (
    <button
      type="button"
      disabled={busy}
      onClick={onToggle}
      title={`Click para ${value ? 'desactivar' : 'activar'} este recurso para este periodo`}
      className={[
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium transition-colors',
        value
          ? 'bg-emerald-50 border-emerald-300 text-emerald-700 hover:bg-emerald-100'
          : 'bg-slate-50 border-slate-200 text-slate-400 hover:bg-slate-100',
        busy ? 'opacity-60 cursor-wait' : 'cursor-pointer',
      ].join(' ')}
    >
      <span className={value ? '' : 'opacity-50'}>{value ? '●' : '○'}</span>
      {label}
    </button>
  )
}

export default function PeriodosPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState(false)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(empty())
  const [apiError, setApiError] = useState(null)
  // Estado para el diálogo de eliminación con preview
  const [delTarget, setDelTarget] = useState(null)
  const [delPreview, setDelPreview] = useState(null)
  const [delLoading, setDelLoading] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['periodos'],
    queryFn: () => getPeriodos().then((r) => r.data?.results ?? r.data ?? []),
  })

  const openCreate = () => { setSelected(null); setForm(empty()); setModal(true) }
  const openEdit = (row) => {
    setSelected(row)
    setForm({
      clave: row.clave,
      fecha_inicio: row.fecha_inicio,
      fecha_fin: row.fecha_fin,
      activo_cartas: !!row.activo_cartas,
      activo_requisitos: !!row.activo_requisitos,
      activo_autoevaluacion: !!row.activo_autoevaluacion,
      estado: row.estado,
    })
    setModal(true)
  }
  const closeModal = () => { setModal(false); setApiError(null) }

  const saveMut = useMutation({
    mutationFn: (d) => (
      selected ? updatePeriodo(selected.id, d) : createPeriodo(d)
    ),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['periodos'] }); closeModal() },
    onError: (e) => setApiError(parseApiError(e.response?.data, 'Error al guardar.')),
  })
  const delMut = useMutation({
    mutationFn: (id) => deletePeriodo(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['periodos'] })
      setDelTarget(null); setDelPreview(null)
    },
    onError: (e) => setApiError(parseApiError(e.response?.data, 'No se pudo eliminar este periodo.')),
  })

  // Pide al backend el conteo de dependencias antes de mostrar la confirmación.
  const abrirDialogoEliminar = async (row) => {
    setApiError(null)
    setDelTarget(row)
    setDelPreview(null)
    setDelLoading(true)
    try {
      const { data } = await previewEliminacionPeriodo(row.id)
      setDelPreview(data)
    } catch (e) {
      setApiError(parseApiError(e.response?.data, 'Error al consultar dependencias.'))
      setDelTarget(null)
    } finally {
      setDelLoading(false)
    }
  }
  const cerrarDialogoEliminar = () => {
    setDelTarget(null); setDelPreview(null); setDelLoading(false)
  }

  // Mutación inline para flipear un flag de recurso desde la tabla.
  const toggleMut = useMutation({
    mutationFn: ({ id, field, value }) => updatePeriodo(id, { [field]: value }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['periodos'] }),
    onError: (e) => setApiError(parseApiError(e.response?.data, 'Error al cambiar el estado del periodo.')),
  })
  const toggleFlag = (row, field) => toggleMut.mutate({ id: row.id, field, value: !row[field] })

  const columns = [
    { key: 'clave', label: 'Clave', className: 'w-20 font-mono' },
    { key: 'fecha_inicio', label: 'Inicio', className: 'w-28' },
    { key: 'fecha_fin', label: 'Fin', className: 'w-28' },
    {
      key: 'flags', label: 'Activo para…',
      render: (_, row) => {
        const cell = (label, flagField) => (
          <FlagChip
            label={label}
            value={row[flagField]}
            busy={toggleMut.isPending}
            onToggle={() => toggleFlag(row, flagField)}
          />
        )
        return (
          <div className="flex flex-wrap gap-2">
            {cell('Cartas', 'activo_cartas')}
            {cell('Requisitos', 'activo_requisitos')}
            {cell('Autoevaluación', 'activo_autoevaluacion')}
          </div>
        )
      },
    },
    { key: 'estado', label: 'Estado', className: 'w-24', render: (v) => <Badge label={v ? 'ACTIVO' : 'INACTIVO'} variant={v ? 'ACTIVO' : 'INACTIVO'} /> },
    {
      key: 'actions', label: '', className: 'w-40 text-right',
      render: (_, row) => {
        const activo = row.activo_cartas || row.activo_requisitos || row.activo_autoevaluacion
        return (
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>Editar</Button>
            <Button
              size="sm"
              variant="danger"
              disabled={activo}
              title={activo
                ? 'Desactiva los flags del periodo para poder eliminarlo'
                : 'Eliminar periodo y todos sus documentos'}
              onClick={() => abrirDialogoEliminar(row)}
            >
              Eliminar
            </Button>
          </div>
        )
      },
    },
  ]

  const f = (key) => (e) => setForm((p) => ({ ...p, [key]: e.target.value }))

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Periodos</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Cada periodo puede estar activo independientemente para cada tipo de
            recurso. Los profesores no eligen el periodo manualmente: al crear
            una Carta Temática o un Requisito de Recuperación, el sistema asigna
            el periodo cuyo flag correspondiente esté activado.
          </p>
        </div>
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

          <div>
            <p className="text-sm font-medium text-slate-700 mb-2">Activo para…</p>
            <div className="space-y-2">
              {[
                ['activo_cartas',         'Cartas Temáticas'],
                ['activo_requisitos',     'Requisitos de Recuperación'],
                ['activo_autoevaluacion', 'Autoevaluación'],
              ].map(([flagKey, label]) => (
                <label key={flagKey} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form[flagKey]}
                    onChange={(e) => setForm((p) => ({ ...p, [flagKey]: e.target.checked }))}
                    className="h-4 w-4 accent-indigo-600"
                  />
                  <span className="text-sm text-slate-700">{label}</span>
                </label>
              ))}
            </div>
            <p className="text-xs text-slate-400 mt-2">
              Solo puede haber un periodo activo por cada recurso. Si activas uno aquí,
              el periodo que lo tuviera activo se desactivará automáticamente.
            </p>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.estado}
              onChange={(e) => setForm((p) => ({ ...p, estado: e.target.checked }))}
              className="h-4 w-4 accent-indigo-600"
            />
            <span className="text-sm text-slate-700">Habilitado (visible para todos)</span>
          </label>
        </div>
      </Modal>

      {/* Modal de confirmación de eliminación en cascada */}
      <Modal
        open={!!delTarget}
        onClose={cerrarDialogoEliminar}
        size="lg"
        title={`Eliminar periodo ${delTarget?.clave ?? ''}`}
        footer={<>
          <Button variant="secondary" onClick={cerrarDialogoEliminar}>Cancelar</Button>
          <Button
            variant="danger"
            disabled={!delPreview?.puede_eliminar}
            loading={delMut.isPending}
            onClick={() => delMut.mutate(delTarget.id)}
          >
            Eliminar periodo y todo lo asociado
          </Button>
        </>}
      >
        {delLoading || !delPreview ? (
          <p className="text-sm text-slate-500">Calculando dependencias…</p>
        ) : !delPreview.puede_eliminar ? (
          <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
            {delPreview.razon_bloqueo}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-lg bg-rose-50 border border-rose-200 px-4 py-3 text-sm text-rose-800">
              <p className="font-semibold mb-1">
                Esta acción es irreversible.
              </p>
              <p>
                Se borrarán el periodo <strong>{delTarget.clave}</strong> y todos los
                documentos, formularios y respuestas que tengan ese periodo asignado.
                Los documentos de otros periodos no se ven afectados.
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-700 mb-2">
                Registros que se eliminarán en cascada:
              </p>
              <ul className="text-sm text-slate-700 space-y-1">
                {[
                  ['Cartas Temáticas',                 delPreview.dependencias.cartas_tematicas],
                  ['Requisitos de Recuperación',       delPreview.dependencias.requisitos_recuperacion],
                  ['Formularios de Autoevaluación',    delPreview.dependencias.formularios_autoevaluacion],
                  ['Respuestas a Autoevaluación',      delPreview.dependencias.respuestas_autoevaluacion],
                ].map(([label, count]) => (
                  <li key={label} className="flex justify-between border-b border-slate-100 py-1">
                    <span>{label}</span>
                    <span className={count > 0 ? 'font-semibold text-rose-700' : 'text-slate-400'}>
                      {count}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
