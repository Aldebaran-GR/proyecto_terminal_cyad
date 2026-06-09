/**
 * Crear / Editar Requisito de Recuperación (Evaluación de Recuperación).
 *
 * Tras el rediseño de junio 2026: documento plano con campos de texto libre.
 * El "lugar" es texto libre para incluir liga/contraseña si es remoto.
 * El periodo se asigna automáticamente desde el activo para Requisitos.
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRequisito, createRequisito, updateRequisito, cambiarEstadoRequisito,
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

export default function RequisitoFormPage() {
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
  const { data: activos } = useQuery({
    queryKey: ['periodos-activos'],
    queryFn: () => getPeriodosActivos().then((r) => r.data),
  })
  const periodoRequisitos = activos?.requisitos ?? null

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

  /* ── Documento existente ── */
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
        lugar: requisito.lugar || '',
        duracion_aprox: requisito.duracion_aprox || '',
        fecha_hora: requisito.fecha_hora || '',
        recursos_necesarios: requisito.recursos_necesarios || '',
        requisitos: requisito.requisitos || '',
        notas: requisito.notas || '',
      })
    }
  }, [requisito, reset])

  const [publicarTras, setPublicarTras] = useState(false)

  /* ── Mutación: guarda (y opcionalmente publica) ── */
  const mutation = useMutation({
    mutationFn: async (payload) => {
      const r = isEdit ? await updateRequisito(id, payload) : await createRequisito(payload)
      const savedId = r.data.id
      if (publicarTras) {
        await cambiarEstadoRequisito(savedId, 'PUBLICADO')
      }
      return savedId
    },
    onSuccess: (savedId) => {
      qc.invalidateQueries({ queryKey: ['requisitos'] })
      qc.invalidateQueries({ queryKey: ['requisitos', 'dashboard'] })
      if (publicarTras && savedId) {
        navigate(`/profesor/requisitos/${savedId}/preview`)
      } else {
        navigate('/profesor/requisitos')
      }
    },
    onError: (e) => {
      const raw = e.response?.data
      const data = raw?.errors ?? raw ?? {}
      setApiError(
        data?.non_field_errors?.[0]
        || data?.detail
        || data?.periodo?.[0]
        || data?.uea?.[0]
        || data?.nombre_grupo?.[0]
        || data?.id_grupo?.[0]
        || (typeof data === 'string' ? data : null)
        || 'Error al guardar el documento.'
      )
    },
  })

  const onSubmit = (form) => {
    setApiError(null)
    if (!isEdit && !periodoRequisitos) {
      setApiError(
        'No hay un periodo activo para Requisitos de Recuperación. Pide al ' +
        'administrador que active uno en Catálogos → Periodos.'
      )
      return
    }
    mutation.mutate({
      uea: Number(form.uea),
      nombre_grupo: form.nombre_grupo,
      id_grupo: form.id_grupo,
      horario: form.horario,
      modalidad: form.modalidad || '',
      lugar: form.lugar || '',
      duracion_aprox: form.duracion_aprox || '',
      fecha_hora: form.fecha_hora || '',
      recursos_necesarios: form.recursos_necesarios || '',
      requisitos: form.requisitos || '',
      notas: form.notas || '',
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
        <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>
      )}

      {isEdit && requisito && requisito.estado !== 'BORRADOR' && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          Este requisito está en estado <strong>{requisito.estado}</strong>.
          Para editarlo, primero{' '}
          <Link to={`/profesor/requisitos/${requisito.id}/preview`} className="underline">
            ábrelo en vista previa y despublícalo
          </Link>.
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
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
              {isEdit && requisito ? (
                <div className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 text-sm text-slate-700">
                  {requisito.periodo_clave ?? '—'}
                  <span className="ml-2 text-xs text-slate-400">(no editable)</span>
                </div>
              ) : periodoRequisitos ? (
                <div className="rounded-lg bg-indigo-50 border border-indigo-200 px-3 py-2 text-sm text-indigo-800">
                  {periodoRequisitos.clave}
                  <span className="ml-2 text-xs text-indigo-600/70">
                    activo para Requisitos
                  </span>
                </div>
              ) : (
                <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
                  Sin periodo activo para Requisitos. Contacta al administrador.
                </div>
              )}
            </FormField>

            <FormField label="Modalidad de la UEA">
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

        {/* ── Detalles de la evaluación ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Detalles de la evaluación</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <FormField
                label="Lugar"
                hint="Texto libre. Si es remoto, incluye liga y contraseña."
              >
                <textarea
                  {...register('lugar')}
                  rows={2}
                  placeholder="ej. Aula H-204 / Liga Zoom: https://… contraseña: 1234"
                  className={inputCls}
                />
              </FormField>
            </div>
            <FormField label="Duración aproximada">
              <input {...register('duracion_aprox')} className={inputCls} placeholder="ej. 2 horas" />
            </FormField>
            <FormField label="Fecha y hora">
              <input {...register('fecha_hora')} className={inputCls}
                placeholder="ej. Lunes 15 de mayo, 10:00 h" />
            </FormField>
          </div>
        </div>

        {/* ── Contenido ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Contenido</SectionTitle>
          <FormField label="Recursos necesarios" hint="Materiales, herramientas, etc.">
            <textarea {...register('recursos_necesarios')} rows={3} className={inputCls}
              placeholder="ej. Papel, cartulina, lápices, escuadras…" />
          </FormField>
          <FormField label="Requisitos" hint="Ej. investigación, maqueta, % de tareas entregadas, etc.">
            <textarea {...register('requisitos')} rows={4} className={inputCls}
              placeholder="ej. Investigación documental + maqueta a escala 1:50 + ≥80% de tareas entregadas" />
          </FormField>
          <FormField label="Notas" hint="Aclaraciones o comentarios adicionales (opcional).">
            <textarea {...register('notas')} rows={3} className={inputCls} />
          </FormField>
        </div>

        {/* ── Footer ── */}
        <div className="flex justify-end gap-3 pb-8 flex-wrap">
          <Link to="/profesor/requisitos">
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
            title="Guarda y deja el documento visible en /publico/requisitos/{id}"
          >
            {isEdit ? 'Guardar y publicar' : 'Crear y publicar'}
          </Button>
        </div>
      </form>
    </div>
  )
}
