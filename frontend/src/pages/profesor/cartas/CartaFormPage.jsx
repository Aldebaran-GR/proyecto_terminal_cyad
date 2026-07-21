/**
 * Crear / Editar Carta Temática.
 *
 * Tras el rediseño de junio 2026 la Carta Temática es un documento plano
 * de campos de texto libre — sin temas/subtemas/bibliografía estructurada
 * ni ponderaciones. El periodo se asigna automáticamente desde el periodo
 * activo para Cartas Temáticas (no se ofrece selector al profesor).
 */
import { useEffect, useMemo, useState } from 'react'
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
  { key: 'enlace',                      label: 'Enlace (clases en línea / asesorías)',
    hint: 'Pega una o varias ligas (Meet, Zoom, calendario, etc.). Una por línea.' },
  { key: 'calendarizacion_actividades', label: 'Calendarización de actividades' },
]

export default function CartaFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isEdit = Boolean(id)

  const [apiError, setApiError] = useState(null)

  // Selección de UEA por búsqueda libre (clave o nombre). El profesor escribe,
  // elige una opción de la lista y queda seleccionada. Sin navegación
  // jerárquica por licenciatura/trimestre.
  const [busquedaUEA, setBusquedaUEA] = useState('')

  const {
    register, handleSubmit, reset, setValue, watch, formState: { errors },
  } = useForm({ defaultValues: { modalidad: '', uea: '' } })

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

  // UEA actualmente seleccionada (objeto completo) para mostrarla.
  const ueaId = watch('uea')
  const ueaSeleccionada = useMemo(
    () => ueas.find((u) => String(u.id) === String(ueaId)) || null,
    [ueas, ueaId],
  )

  // Resultados del buscador: top 10 coincidencias por clave o nombre.
  const resultadosBusqueda = useMemo(() => {
    const q = busquedaUEA.trim().toLowerCase()
    if (!q) return []
    return ueas
      .filter((u) =>
        (u.clave || '').toLowerCase().includes(q)
        || (u.nombre || '').toLowerCase().includes(q)
      )
      .slice(0, 10)
  }, [ueas, busquedaUEA])

  // Elegir una UEA desde el buscador: la marca como elegida y limpia la búsqueda.
  const seleccionarUEADesdeBusqueda = (u) => {
    setValue('uea', String(u.id), { shouldValidate: true })
    setBusquedaUEA('')
  }

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
      const raw = e.response?.data
      const data = raw?.errors ?? raw ?? {}
      setApiError(
        data?.periodo?.[0]
        || data?.non_field_errors?.[0]
        || data?.detail
        || data?.uea?.[0]
        || data?.nombre_grupo?.[0]
        || data?.id_grupo?.[0]
        || (typeof data === 'string' ? data : null)
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
        {/* ── Selección de UEA (por búsqueda) ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Selección de UEA</SectionTitle>
          <p className="text-xs text-slate-500 -mt-2">
            Búscala por clave o nombre y selecciónala de la lista.
          </p>

          {/* Campo oculto registrado para validación del formulario */}
          <input type="hidden" {...register('uea', { required: 'Selecciona una UEA' })} />

          {/* UEA seleccionada */}
          {ueaSeleccionada && (
            <div className="flex items-center justify-between gap-3 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2">
              <div className="min-w-0 text-sm">
                <span className="font-mono text-slate-500 mr-2">{ueaSeleccionada.clave}</span>
                <span className="text-slate-800">{ueaSeleccionada.nombre}</span>
                {ueaSeleccionada.licenciatura_nombre && (
                  <span className="ml-2 text-xs text-slate-500">
                    · {ueaSeleccionada.licenciatura_nombre}
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => setValue('uea', '', { shouldValidate: true })}
                className="shrink-0 text-xs font-medium text-rose-600 hover:underline"
              >
                Cambiar
              </button>
            </div>
          )}

          {/* Buscador por clave/nombre */}
          <FormField
            label="Buscar UEA"
            error={errors.uea?.message}
            required={!ueaSeleccionada}
            hint="Escribe parte de la clave o del nombre y selecciona una opción."
          >
            <div className="relative">
              <input
                type="text"
                value={busquedaUEA}
                onChange={(e) => setBusquedaUEA(e.target.value)}
                placeholder="ej. 1100023 o Diseño Industrial"
                className={inputCls}
                autoComplete="off"
              />
              {resultadosBusqueda.length > 0 && (
                <ul className="absolute z-10 mt-1 w-full max-h-60 overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg">
                  {resultadosBusqueda.map((u) => (
                    <li key={u.id}>
                      <button
                        type="button"
                        onClick={() => seleccionarUEADesdeBusqueda(u)}
                        className="w-full text-left px-3 py-2 hover:bg-indigo-50 text-sm border-b border-slate-100 last:border-0"
                      >
                        <span className="font-mono text-slate-500 mr-2">{u.clave}</span>
                        <span className="text-slate-800">{u.nombre}</span>
                        {u.licenciatura_nombre && (
                          <span className="ml-2 text-xs text-slate-400">· {u.licenciatura_nombre}</span>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {busquedaUEA.trim() && resultadosBusqueda.length === 0 && (
                <p className="mt-1 text-xs text-slate-400">Sin coincidencias.</p>
              )}
            </div>
          </FormField>
        </div>

        {/* ── Información del grupo ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Información del grupo</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
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

            <FormField label="Modalidad">
              <select {...register('modalidad')} className={inputCls}>
                <option value="">-- Opcional --</option>
                <option value="PRESENCIAL">Presencial</option>
                <option value="REMOTO">Remoto</option>
                <option value="MIXTO">Mixto</option>
              </select>
            </FormField>

            <FormField label="Nombre del grupo" error={errors.nombre_grupo?.message} required>
              <input {...register('nombre_grupo', { required: 'Requerido' })}
                placeholder="ej. Grupo A" className={inputCls} />
            </FormField>

            <FormField label="ID del grupo" error={errors.id_grupo?.message} required>
              <input {...register('id_grupo', { required: 'Requerido' })}
                placeholder="ej. 2026-I-A1" className={inputCls} />
            </FormField>

            <div className="col-span-2">
              <FormField label="Horario" error={errors.horario?.message} required>
                <input {...register('horario', { required: 'Requerido' })}
                  placeholder="ej. Lun-Mié 9:00-11:00" className={inputCls} />
              </FormField>
            </div>
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
