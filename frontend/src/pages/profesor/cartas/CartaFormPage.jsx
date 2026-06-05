/**
 * Crear / Editar Carta Temática.
 *
 * Estrategia de formulario:
 *   - react-hook-form para los campos base (uea, periodo, grupo, etc.)
 *   - useState para las secciones dinámicas (temas, bibliografías, criterios)
 *   - Al enviar se consolida todo en un solo payload
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getCarta, createCarta, updateCarta,
} from '../../../api/documentos'
import { getUEA, getPeriodos } from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Alert from '../../../components/ui/Alert'
import FormField, { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

/* ─── helpers ─────────────────────────────────────────────── */
const emptyTema = () => ({ nombre: '', objetivo: '', num_sesiones: 1, subtemas: [] })
const emptySubtema = () => ({ descripcion: '' })
const emptyBib = () => ({ tipo: 'BASICA', referencia: '' })
const emptyCriterio = () => ({ descripcion: '', ponderacion: '' })

function SectionTitle({ children }) {
  return (
    <h2 className="text-base font-semibold text-slate-800 border-b border-slate-200 pb-2 mb-4">
      {children}
    </h2>
  )
}

/* ─── Componente inline para subtemas ─────────────────────── */
function SubtemasEditor({ subtemas, onChange }) {
  const add = () => onChange([...subtemas, emptySubtema()])
  const remove = (i) => onChange(subtemas.filter((_, idx) => idx !== i))
  const update = (i, val) =>
    onChange(subtemas.map((s, idx) => (idx === i ? { ...s, descripcion: val } : s)))

  return (
    <div className="ml-4 space-y-2">
      {subtemas.map((s, i) => (
        <div key={i} className="flex gap-2">
          <input
            value={s.descripcion}
            onChange={(e) => update(i, e.target.value)}
            placeholder={`Subtema ${i + 1}`}
            className={inputCls + ' flex-1 text-xs'}
          />
          <button
            type="button"
            onClick={() => remove(i)}
            className="rounded px-2 text-slate-400 hover:text-rose-500"
          >
            ×
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="text-xs text-indigo-600 hover:underline"
      >
        + Añadir subtema
      </button>
    </div>
  )
}

/* ─── Página principal ─────────────────────────────────────── */
export default function CartaFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isEdit = Boolean(id)

  const [apiError, setApiError] = useState(null)
  const [temas, setTemas] = useState([emptyTema()])
  const [bibliografias, setBibliografias] = useState([emptyBib()])
  const [criterios, setCriterios] = useState([emptyCriterio()])

  /* ── Form base ── */
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm({ defaultValues: { modalidad: '' } })

  /* ── Cargar catálogos ── */
  const { data: ueas = [] } = useQuery({
    queryKey: ['uea-list'],
    queryFn: () => getUEA({ estado: true }).then((r) => r.data?.results ?? r.data ?? []),
  })
  const { data: periodos = [] } = useQuery({
    queryKey: ['periodos-list'],
    queryFn: () => getPeriodos().then((r) => r.data?.results ?? r.data ?? []),
  })

  /* ── Cargar carta existente (edición) ── */
  const { data: cartaExistente } = useQuery({
    queryKey: ['carta', id],
    queryFn: () => getCarta(id).then((r) => r.data),
    enabled: isEdit,
  })

  useEffect(() => {
    if (cartaExistente) {
      reset({
        uea: String(cartaExistente.uea),
        periodo: String(cartaExistente.periodo),
        nombre_grupo: cartaExistente.nombre_grupo,
        id_grupo: cartaExistente.id_grupo,
        horario: cartaExistente.horario,
        modalidad: cartaExistente.modalidad || '',
        objetivo_general: cartaExistente.objetivo_general || '',
        presentacion: cartaExistente.presentacion || '',
      })
      setTemas(
        cartaExistente.temas?.length
          ? cartaExistente.temas.map((t) => ({
              nombre: t.nombre,
              objetivo: t.objetivo || '',
              num_sesiones: t.num_sesiones,
              subtemas: (t.subtemas || []).map((s) => ({ descripcion: s.descripcion })),
            }))
          : [emptyTema()]
      )
      setBibliografias(
        cartaExistente.bibliografias?.length
          ? cartaExistente.bibliografias.map((b) => ({ tipo: b.tipo, referencia: b.referencia }))
          : [emptyBib()]
      )
      setCriterios(
        cartaExistente.criterios?.length
          ? cartaExistente.criterios.map((c) => ({
              descripcion: c.descripcion,
              ponderacion: String(c.ponderacion),
            }))
          : [emptyCriterio()]
      )
    }
  }, [cartaExistente, reset])

  /* ── Mutaciones ── */
  const mutation = useMutation({
    mutationFn: (payload) =>
      isEdit ? updateCarta(id, payload) : createCarta(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cartas'] })
      navigate('/profesor/cartas')
    },
    onError: (e) => {
      const data = e.response?.data
      setApiError(
        data?.non_field_errors?.[0] ||
        data?.detail ||
        JSON.stringify(data) ||
        'Error al guardar la carta.'
      )
    },
  })

  /* ── Helpers dinámicos ── */
  const updateTema = (i, key, val) =>
    setTemas((prev) => prev.map((t, idx) => (idx === i ? { ...t, [key]: val } : t)))

  const sumPonderaciones = criterios.reduce(
    (acc, c) => acc + (Number(c.ponderacion) || 0), 0
  )

  /* ── Submit ── */
  const onSubmit = (baseData) => {
    setApiError(null)

    if (criterios.length > 0 && sumPonderaciones !== 100) {
      setApiError(`La suma de ponderaciones debe ser 100% (actualmente: ${sumPonderaciones}%).`)
      return
    }

    const payload = {
      uea: Number(baseData.uea),
      periodo: Number(baseData.periodo),
      nombre_grupo: baseData.nombre_grupo,
      id_grupo: baseData.id_grupo,
      horario: baseData.horario,
      modalidad: baseData.modalidad || '',
      objetivo_general: baseData.objetivo_general || '',
      presentacion: baseData.presentacion || '',
      temas: temas
        .filter((t) => t.nombre.trim())
        .map((t, i) => ({
          orden: i + 1,
          nombre: t.nombre,
          objetivo: t.objetivo || '',
          num_sesiones: Number(t.num_sesiones) || 1,
          subtemas: t.subtemas
            .filter((s) => s.descripcion.trim())
            .map((s, j) => ({ orden: j + 1, descripcion: s.descripcion })),
        })),
      bibliografias: bibliografias
        .filter((b) => b.referencia.trim())
        .map((b) => ({ tipo: b.tipo, referencia: b.referencia })),
      criterios: criterios
        .filter((c) => c.descripcion.trim())
        .map((c) => ({ descripcion: c.descripcion, ponderacion: Number(c.ponderacion) })),
    }
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
        <Alert type="error" onClose={() => setApiError(null)}>
          {apiError}
        </Alert>
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
                  <option key={u.id} value={u.id}>
                    {u.nombre}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Periodo" error={errors.periodo?.message} required>
              <select {...register('periodo', { required: 'Requerido' })} className={inputCls}>
                <option value="">-- Selecciona --</option>
                {periodos.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.clave}
                  </option>
                ))}
              </select>
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

        {/* ── Objetivo y Presentación ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Objetivo y Presentación</SectionTitle>
          <FormField label="Objetivo general">
            <textarea
              {...register('objetivo_general')}
              rows={3}
              placeholder="Objetivo general de la UEA para este grupo"
              className={inputCls}
            />
          </FormField>
          <FormField label="Presentación">
            <textarea
              {...register('presentacion')}
              rows={3}
              placeholder="Presentación o descripción del curso"
              className={inputCls}
            />
          </FormField>
        </div>

        {/* ── Temas ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Temas y Subtemas</SectionTitle>
          <div className="space-y-4">
            {temas.map((tema, i) => (
              <div key={i} className="rounded-lg border border-slate-100 bg-slate-50 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase">
                    Tema {i + 1}
                  </span>
                  <button
                    type="button"
                    onClick={() => setTemas((prev) => prev.filter((_, idx) => idx !== i))}
                    className="text-xs text-slate-400 hover:text-rose-500"
                  >
                    Eliminar tema
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Nombre del tema *
                    </label>
                    <input
                      value={tema.nombre}
                      onChange={(e) => updateTema(i, 'nombre', e.target.value)}
                      placeholder="Nombre del tema"
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Sesiones
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={tema.num_sesiones}
                      onChange={(e) => updateTema(i, 'num_sesiones', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">
                    Objetivo del tema
                  </label>
                  <textarea
                    value={tema.objetivo}
                    onChange={(e) => updateTema(i, 'objetivo', e.target.value)}
                    rows={2}
                    placeholder="Objetivo específico de este tema"
                    className={inputCls + ' text-sm'}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">
                    Subtemas
                  </label>
                  <SubtemasEditor
                    subtemas={tema.subtemas}
                    onChange={(sub) => updateTema(i, 'subtemas', sub)}
                  />
                </div>
              </div>
            ))}
          </div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setTemas((prev) => [...prev, emptyTema()])}
          >
            + Añadir tema
          </Button>
        </div>

        {/* ── Bibliografía ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <SectionTitle>Bibliografía</SectionTitle>
          <div className="space-y-3">
            {bibliografias.map((bib, i) => (
              <div key={i} className="flex gap-2 items-start">
                <select
                  value={bib.tipo}
                  onChange={(e) =>
                    setBibliografias((prev) =>
                      prev.map((b, idx) => (idx === i ? { ...b, tipo: e.target.value } : b))
                    )
                  }
                  className={inputCls + ' w-40 shrink-0'}
                >
                  <option value="BASICA">Básica</option>
                  <option value="COMPLEMENTARIA">Complementaria</option>
                </select>
                <input
                  value={bib.referencia}
                  onChange={(e) =>
                    setBibliografias((prev) =>
                      prev.map((b, idx) =>
                        idx === i ? { ...b, referencia: e.target.value } : b
                      )
                    )
                  }
                  placeholder="Referencia bibliográfica completa"
                  className={inputCls + ' flex-1'}
                />
                <button
                  type="button"
                  onClick={() =>
                    setBibliografias((prev) => prev.filter((_, idx) => idx !== i))
                  }
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
            onClick={() => setBibliografias((prev) => [...prev, emptyBib()])}
          >
            + Añadir referencia
          </Button>
        </div>

        {/* ── Criterios de Evaluación ── */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-4">
          <div className="flex items-center justify-between">
            <SectionTitle>Criterios de Evaluación</SectionTitle>
            <span
              className={`text-sm font-medium ${
                sumPonderaciones === 100
                  ? 'text-emerald-600'
                  : sumPonderaciones > 100
                  ? 'text-rose-600'
                  : 'text-slate-500'
              }`}
            >
              Total: {sumPonderaciones}% {sumPonderaciones !== 100 && '(debe ser 100%)'}
            </span>
          </div>
          <div className="space-y-3">
            {criterios.map((c, i) => (
              <div key={i} className="flex gap-2 items-start">
                <input
                  value={c.descripcion}
                  onChange={(e) =>
                    setCriterios((prev) =>
                      prev.map((cr, idx) =>
                        idx === i ? { ...cr, descripcion: e.target.value } : cr
                      )
                    )
                  }
                  placeholder="Descripción del criterio"
                  className={inputCls + ' flex-1'}
                />
                <div className="flex items-center gap-1 shrink-0">
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={c.ponderacion}
                    onChange={(e) =>
                      setCriterios((prev) =>
                        prev.map((cr, idx) =>
                          idx === i ? { ...cr, ponderacion: e.target.value } : cr
                        )
                      )
                    }
                    placeholder="0"
                    className={inputCls + ' w-20 text-center'}
                  />
                  <span className="text-sm text-slate-500">%</span>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setCriterios((prev) => prev.filter((_, idx) => idx !== i))
                  }
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
            onClick={() => setCriterios((prev) => [...prev, emptyCriterio()])}
          >
            + Añadir criterio
          </Button>
        </div>

        {/* ── Footer ── */}
        <div className="flex justify-end gap-3 pb-8">
          <Link to="/profesor/cartas">
            <Button type="button" variant="secondary">
              Cancelar
            </Button>
          </Link>
          <Button type="submit" loading={mutation.isPending}>
            {isEdit ? 'Guardar cambios' : 'Crear carta'}
          </Button>
        </div>
      </form>
    </div>
  )
}
