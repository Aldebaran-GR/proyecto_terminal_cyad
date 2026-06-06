/**
 * Crear / Editar Requisito de Recuperación.
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getRequisito, createRequisito, updateRequisito } from '../../../api/documentos'
import { getUEA, getPeriodosActivos } from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Alert from '../../../components/ui/Alert'
import FormField, { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

const emptyItem = () => ({ descripcion: '' })

function SectionTitle({ children }) {
  return (
    <h2 className="text-base font-semibold text-slate-800 border-b border-slate-200 pb-2 mb-4">
      {children}
    </h2>
  )
}

export default function RequisitoFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isEdit = Boolean(id)

  const [apiError, setApiError] = useState(null)
  const [items, setItems] = useState([emptyItem()])

  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    defaultValues: { modalidad: '', espacio_modalidad: '' },
  })

  /* ── Catálogos ── */
  const { data: ueas = [] } = useQuery({
    queryKey: ['uea-list'],
    queryFn: () => getUEA({ estado: true }).then((r) => r.data?.results ?? r.data ?? []),
  })
  // El periodo del Requisito de Recuperación se asigna automáticamente desde
  // el periodo marcado como "activo para Requisitos" por el admin.
  const { data: activos } = useQuery({
    queryKey: ['periodos-activos'],
    queryFn: () => getPeriodosActivos().then((r) => r.data),
  })
  const periodoRequisitos = activos?.requisitos ?? null

  /* ── Cargar existente ── */
  const { data: requisito } = useQuery({
    queryKey: ['requisito', id],
    queryFn: () => getRequisito(id).then((r) => r.data),
    enabled: isEdit,
  })

  useEffect(() => {
    if (requisito) {
      reset({
        uea: String(requisito.uea),
        nombre_grupo: requisito.nombre_grupo,
        id_grupo: requisito.id_grupo,
        horario: requisito.horario,
        modalidad: requisito.modalidad || '',
        espacio_modalidad: requisito.espacio_modalidad || '',
        indicaciones: requisito.indicaciones || '',
      })
      setItems(
        requisito.items?.length
          ? requisito.items.map((it) => ({ descripcion: it.descripcion }))
          : [emptyItem()]
      )
    }
  }, [requisito, reset])

  /* ── Mutación ── */
  const mutation = useMutation({
    mutationFn: (payload) =>
      isEdit ? updateRequisito(id, payload) : createRequisito(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['requisitos'] })
      navigate('/profesor/requisitos')
    },
    onError: (e) => {
      const data = e.response?.data
      setApiError(
        data?.non_field_errors?.[0] || data?.detail || 'Error al guardar el requisito.'
      )
    },
  })

  const onSubmit = (baseData) => {
    setApiError(null)
    if (!isEdit && !periodoRequisitos) {
      setApiError(
        'No hay un periodo activo para Requisitos de Recuperación. Pide al ' +
        'administrador que active uno en Catálogos → Periodos.'
      )
      return
    }
    // `periodo` lo asigna el backend según el periodo activo para Requisitos.
    mutation.mutate({
      uea: Number(baseData.uea),
      nombre_grupo: baseData.nombre_grupo,
      id_grupo: baseData.id_grupo,
      horario: baseData.horario,
      modalidad: baseData.modalidad || '',
      espacio_modalidad: baseData.espacio_modalidad || '',
      indicaciones: baseData.indicaciones || '',
      items: items
        .filter((it) => it.descripcion.trim())
        .map((it, i) => ({ orden: i + 1, descripcion: it.descripcion })),
    })
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to="/profesor/requisitos" className="text-slate-400 hover:text-slate-600">
          ← Volver
        </Link>
        <h1 className="text-xl font-bold text-slate-900">
          {isEdit ? 'Editar Requisito de Recuperación' : 'Nuevo Requisito de Recuperación'}
        </h1>
        {requisito && <Badge label={requisito.estado} variant={requisito.estado} />}
      </div>

      {apiError && (
        <Alert type="error" onClose={() => setApiError(null)}>
          {apiError}
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* ── Información del grupo ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Información del grupo</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="UEA" error={errors.uea?.message} required>
              <select {...register('uea', { required: 'Requerido' })} className={inputCls}>
                <option value="">-- Selecciona --</option>
                {ueas.map((u) => (
                  <option key={u.id} value={u.id}>{u.nombre}</option>
                ))}
              </select>
            </FormField>

            <FormField label="Periodo (asignado automáticamente)">
              {isEdit && requisito ? (
                <div className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 text-sm text-slate-700">
                  {requisito.periodo_clave ?? '—'}
                  <span className="ml-2 text-xs text-slate-400">(no editable)</span>
                </div>
              ) : periodoRequisitos ? (
                <div className="rounded-lg bg-indigo-50 border border-indigo-200 px-3 py-2 text-sm text-indigo-800">
                  {periodoRequisitos.clave}
                  <span className="ml-2 text-xs text-indigo-600/70">
                    activo para Requisitos de Recuperación
                  </span>
                </div>
              ) : (
                <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
                  Sin periodo activo para Requisitos. Contacta al administrador.
                </div>
              )}
            </FormField>

            <FormField label="Nombre del grupo" error={errors.nombre_grupo?.message} required>
              <input
                {...register('nombre_grupo', { required: 'Requerido' })}
                placeholder="ej. Grupo A"
                className={inputCls}
              />
            </FormField>

            <FormField label="ID del grupo" error={errors.id_grupo?.message} required>
              <input
                {...register('id_grupo', { required: 'Requerido' })}
                placeholder="ej. 2026-I-A1"
                className={inputCls}
              />
            </FormField>

            <FormField label="Horario" error={errors.horario?.message} required>
              <input
                {...register('horario', { required: 'Requerido' })}
                placeholder="ej. Lun-Mié 9:00-11:00"
                className={inputCls}
              />
            </FormField>

            <FormField label="Modalidad de la UEA">
              <select {...register('modalidad')} className={inputCls}>
                <option value="">-- Opcional --</option>
                <option value="PRESENCIAL">Presencial</option>
                <option value="REMOTO">Remoto</option>
                <option value="MIXTO">Mixto</option>
              </select>
            </FormField>
          </div>
        </div>

        {/* ── Detalles de recuperación ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Detalles de Recuperación</SectionTitle>
          <FormField label="Modalidad del espacio de recuperación">
            <select {...register('espacio_modalidad')} className={inputCls}>
              <option value="">-- Opcional --</option>
              <option value="PRESENCIAL">Presencial</option>
              <option value="REMOTO">Remoto</option>
              <option value="MIXTO">Mixto</option>
            </select>
          </FormField>
          <FormField label="Indicaciones generales">
            <textarea
              {...register('indicaciones')}
              rows={4}
              placeholder="Describe las indicaciones generales de recuperación para esta UEA"
              className={inputCls}
            />
          </FormField>
        </div>

        {/* ── Lista de requisitos ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Lista de Requisitos</SectionTitle>
          <div className="space-y-3">
            {items.map((it, i) => (
              <div key={i} className="flex gap-2">
                <span className="mt-2 text-xs text-slate-400 w-6 shrink-0">{i + 1}.</span>
                <input
                  value={it.descripcion}
                  onChange={(e) =>
                    setItems((prev) =>
                      prev.map((item, idx) =>
                        idx === i ? { ...item, descripcion: e.target.value } : item
                      )
                    )
                  }
                  placeholder={`Requisito ${i + 1}`}
                  className={inputCls + ' flex-1'}
                />
                <button
                  type="button"
                  onClick={() => setItems((prev) => prev.filter((_, idx) => idx !== i))}
                  className="mt-2 text-slate-400 hover:text-rose-500"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setItems((prev) => [...prev, emptyItem()])}
          >
            + Añadir requisito
          </Button>
        </div>

        {/* ── Footer ── */}
        <div className="flex justify-end gap-3 pb-8">
          <Link to="/profesor/requisitos">
            <Button type="button" variant="secondary">Cancelar</Button>
          </Link>
          <Button type="submit" loading={mutation.isPending}>
            {isEdit ? 'Guardar cambios' : 'Crear requisito'}
          </Button>
        </div>
      </form>
    </div>
  )
}
