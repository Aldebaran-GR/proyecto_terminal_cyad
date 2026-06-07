/**
 * Crear / Editar Carta Temática.
 *
 * Tras el rediseño de junio 2026 la Carta Temática es un documento plano
 * de campos de texto libre — sin temas/subtemas/bibliografía estructurada
 * ni ponderaciones. El periodo se asigna automáticamente desde el periodo
 * activo para Cartas Temáticas (no se ofrece selector al profesor).
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getCarta, createCarta, updateCarta, cambiarEstadoCarta,
} from '../../../api/documentos'
import { getUEA, getPeriodosActivos } from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Alert from '../../../components/ui/Alert'
import FormField, { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

function SectionTitle({ children }) {
  return (
    <h2 className="text-base font-semibold text-slate-800 border-b border-slate-200 pb-2 mb-4">
      {children}
    </h2>
  )
}

/* ─── Campos de contenido (todos TextField libre) ──────────────────────── */
const CONTENT_FIELDS = [
  { key: 'descripcion_uea',             label: 'Descripción de la UEA',
    hint: 'Breve descripción general de la UEA.' },
  { key: 'objetivo_general',            label: 'Objetivo general' },
  { key: 'objetivos_particulares',      label: 'Objetivos particulares' },
  { key: 'contenido_sintetico',         label: 'Contenido sintético' },
  { key: 'objetivos_aprendizaje',       label: 'Objetivos de aprendizaje' },
  { key: 'requerimientos',              label: 'Requerimientos',
    hint: 'Materiales necesarios.' },
  { key: 'conocimientos_previos',       label: 'Conocimientos previos' },
  { key: 'modalidad_evaluacion',        label: 'Modalidad de evaluación' },
  { key: 'revisiones_asesorias',        label: 'Revisiones / Asesorías' },
  { key: 'bibliografia',                label: 'Bibliografía' },
  { key: 'calendarizacion_actividades', label: 'Calendarización de actividades' },
]

export default function CartaFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isEdit = Boolean(id)

  const [apiError, setApiError] = useState(null)

  const {
    register, handleSubmit, reset, formState: { errors },
  } = useForm({ defaultValues: { modalidad: '' } })

  /* ── Catálogos ── */
  const { data: ueas = [] } = useQuery({
    queryKey: ['uea-list'],
    queryFn: () => getUEA({ estado: true }).then((r) => r.data?.results ?? r.data ?? []),
  })
  // Periodo activo para Cartas Temáticas (no editable por el profesor).
  const { data: activos } = useQuery({
    queryKey: ['periodos-activos'],
    queryFn: () => getPeriodosActivos().then((r) => r.data),
  })
  const periodoCartas = activos?.cartas ?? null

  /* ── Carta existente (edición) ── */
  const { data: cartaExistente } = useQuery({
    queryKey: ['carta', id],
    queryFn: () => getCarta(id).then((r) => r.data),
    enabled: isEdit,
  })

  useEffect(() => {
    if (cartaExistente) {
      const defaults = {
        uea: String(cartaExistente.uea),
        nombre_grupo: cartaExistente.nombre_grupo,
        id_grupo: cartaExistente.id_grupo,
        horario: cartaExistente.horario,
        modalidad: cartaExistente.modalidad || '',
      }
      CONTENT_FIELDS.forEach(({ key }) => {
        defaults[key] = cartaExistente[key] || ''
      })
      reset(defaults)
    }
  }, [cartaExistente, reset])

  // `publicarTras` controla si después de guardar marcamos PUBLICADO.
  // Si el usuario pulsa "Guardar borrador" → false; si pulsa "Guardar y
  // publicar" → true.
  const [publicarTras, setPublicarTras] = useState(false)

  /* ── Mutación: guarda (y, opcionalmente, publica) ── */
  const mutation = useMutation({
    mutationFn: async (payload) => {
      const r = isEdit ? await updateCarta(id, payload) : await createCarta(payload)
      const savedId = r.data.id
      if (publicarTras) {
        await cambiarEstadoCarta(savedId, 'PUBLICADO')
      }
      return savedId
    },
    onSuccess: (savedId) => {
      qc.invalidateQueries({ queryKey: ['cartas'] })
      qc.invalidateQueries({ queryKey: ['cartas', 'dashboard'] })
      // Si publicó, llevarlo a la vista previa para confirmar el resultado.
      if (publicarTras && savedId) {
        navigate(`/profesor/cartas/${savedId}/preview`)
      } else {
        navigate('/profesor/cartas')
      }
    },
    onError: (e) => {
      const data = e.response?.data
      setApiError(
        data?.non_field_errors?.[0]
        || data?.detail
        || data?.periodo?.[0]
        || JSON.stringify(data)
        || 'Error al guardar la carta.'
      )
    },
  })

  /* ── Submit ── */
  const onSubmit = (form) => {
    setApiError(null)
    if (!isEdit && !periodoCartas) {
      setApiError(
        'No hay un periodo activo para Cartas Temáticas. Pide al ' +
        'administrador que active uno en Catálogos → Periodos.'
      )
      return
    }
    // `periodo` se asigna en backend desde el activo para Cartas Temáticas.
    const payload = {
      uea: Number(form.uea),
      nombre_grupo: form.nombre_grupo,
      id_grupo: form.id_grupo,
      horario: form.horario,
      modalidad: form.modalidad || '',
    }
    CONTENT_FIELDS.forEach(({ key }) => {
      payload[key] = form[key] || ''
    })
    mutation.mutate(payload)
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/profesor/cartas" className="text-slate-400 hover:text-slate-600">
            ← Volver
          </Link>
          <h1 className="text-xl font-bold text-slate-900">
            {isEdit ? 'Editar Carta Temática' : 'Nueva Carta Temática'}
          </h1>
          {cartaExistente && (
            <Badge label={cartaExistente.estado} variant={cartaExistente.estado} />
          )}
        </div>
      </div>

      {apiError && (
        <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>
      )}

      {/* Si llegamos al form con una carta no editable, sugerimos despublicar */}
      {isEdit && cartaExistente && cartaExistente.estado !== 'BORRADOR' && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          Esta carta está en estado <strong>{cartaExistente.estado}</strong>.
          Para editarla, primero{' '}
          <Link to={`/profesor/cartas/${cartaExistente.id}/preview`} className="underline">
            ábrela en vista previa y despublícala
          </Link>.
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
        {/* ── Información del grupo ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Información del grupo</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="UEA" error={errors.uea?.message} required>
              <select {...register('uea', { required: 'Requerido' })} className={inputCls}>
                <option value="">-- Selecciona --</option>
                {ueas.map((u) => (
                  <option key={u.id} value={u.id}>{u.clave} — {u.nombre}</option>
                ))}
              </select>
            </FormField>

            <FormField label="Periodo (asignado automáticamente)">
              {isEdit && cartaExistente ? (
                <div className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 text-sm text-slate-700">
                  {cartaExistente.periodo_clave ?? '—'}
                  <span className="ml-2 text-xs text-slate-400">(no editable)</span>
                </div>
              ) : periodoCartas ? (
                <div className="rounded-lg bg-indigo-50 border border-indigo-200 px-3 py-2 text-sm text-indigo-800">
                  {periodoCartas.clave}
                  <span className="ml-2 text-xs text-indigo-600/70">
                    activo para Cartas Temáticas
                  </span>
                </div>
              ) : (
                <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
                  Sin periodo activo para Cartas Temáticas. Contacta al administrador.
                </div>
              )}
            </FormField>

            <FormField label="Nombre del grupo" error={errors.nombre_grupo?.message} required>
              <input {...register('nombre_grupo', { required: 'Requerido' })}
                placeholder="ej. Grupo A" className={inputCls} />
            </FormField>

            <FormField label="ID del grupo" error={errors.id_grupo?.message} required>
              <input {...register('id_grupo', { required: 'Requerido' })}
                placeholder="ej. 2026-I-A1" className={inputCls} />
            </FormField>

            <FormField label="Horario" error={errors.horario?.message} required>
              <input {...register('horario', { required: 'Requerido' })}
                placeholder="ej. Lun-Mié 9:00-11:00" className={inputCls} />
            </FormField>

            <FormField label="Modalidad">
              <select {...register('modalidad')} className={inputCls}>
                <option value="">-- Opcional --</option>
                <option value="PRESENCIAL">Presencial</option>
                <option value="REMOTO">Remoto</option>
                <option value="MIXTO">Mixto</option>
              </select>
            </FormField>
          </div>
        </div>

        {/* ── Contenido ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Contenido</SectionTitle>
          <p className="text-xs text-slate-500 -mt-2 mb-3">
            Todos los campos aceptan texto libre. Los que dejes vacíos no se
            mostrarán en la vista pública.
          </p>
          <div className="space-y-5">
            {CONTENT_FIELDS.map(({ key, label, hint }) => (
              <FormField key={key} label={label} hint={hint}>
                <textarea
                  {...register(key)}
                  rows={3}
                  placeholder={label}
                  className={inputCls}
                />
              </FormField>
            ))}
          </div>
        </div>

        {/* ── Footer ── */}
        <div className="flex justify-end gap-3 pb-8 flex-wrap">
          <Link to="/profesor/cartas">
            <Button type="button" variant="secondary">Cancelar</Button>
          </Link>
          <Button
            type="submit"
            variant="secondary"
            loading={mutation.isPending && !publicarTras}
            onClick={() => setPublicarTras(false)}
          >
            {isEdit ? 'Guardar borrador' : 'Guardar como borrador'}
          </Button>
          <Button
            type="submit"
            loading={mutation.isPending && publicarTras}
            onClick={() => setPublicarTras(true)}
            title="Guarda y deja la carta visible en /publico/cartas/{id}"
          >
            {isEdit ? 'Guardar y publicar' : 'Crear y publicar'}
          </Button>
        </div>
      </form>
    </div>
  )
}
