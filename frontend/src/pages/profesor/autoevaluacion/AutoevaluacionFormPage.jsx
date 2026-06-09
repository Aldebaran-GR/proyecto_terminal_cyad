/**
 * Renderizador dinámico de formularios de Autoevaluación.
 *
 * Flujo:
 *   1. Carga el formulario (GET /formularios-disponibles/:id/)
 *   2. Si ya_respondido → muestra resultado (readonly)
 *   3. Si hay respuesta en borrador → pre-llena las respuestas
 *   4. Render pregunta a pregunta según tipo
 *   5. "Guardar borrador" → POST/PATCH /respuestas/
 *   6. "Enviar" → POST /respuestas/:id/enviar/ → muestra resultado
 */
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createRespuesta,
  enviarRespuesta,
  getFormularioDisponible,
  getRespuesta,
  updateRespuesta,
} from '../../../api/autoevaluacion'
import Alert from '../../../components/ui/Alert'
import Button from '../../../components/ui/Button'
import Loading from '../../../components/ui/Loading'
import { inputCls } from '../../../components/ui/FormField'

/* ─── Colores de nivel ────────────────────────────────────── */
const NIVEL_COLORS = {
  green: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  blue: 'bg-blue-50 border-blue-200 text-blue-800',
  yellow: 'bg-amber-50 border-amber-200 text-amber-800',
  red: 'bg-rose-50 border-rose-200 text-rose-800',
  gray: 'bg-slate-50 border-slate-200 text-slate-800',
}

/* ─── Resultado después de enviar ────────────────────────── */
function ResultCard({ respuesta }) {
  const { puntaje_obtenido, puntaje_maximo, porcentaje, nivel_desempeno } = respuesta
  const colorCls =
    NIVEL_COLORS[nivel_desempeno?.color ?? 'gray'] ?? NIVEL_COLORS.gray
  const pct = porcentaje != null ? Number(porcentaje).toFixed(1) : null

  return (
    <div className="rounded-xl border bg-white p-6 space-y-4 max-w-lg mx-auto text-center">
      <div className="text-4xl font-bold text-slate-900">
        {pct != null ? `${pct}%` : '—'}
      </div>
      {puntaje_maximo > 0 && (
        <p className="text-sm text-slate-500">
          {Number(puntaje_obtenido).toFixed(1)} / {Number(puntaje_maximo).toFixed(1)} pts
        </p>
      )}

      {nivel_desempeno ? (
        <div className={`rounded-lg border p-4 ${colorCls}`}>
          <p className="font-semibold text-lg">{nivel_desempeno.nombre}</p>
          <p className="mt-1 text-sm leading-relaxed">{nivel_desempeno.observacion}</p>
        </div>
      ) : (
        <p className="text-sm text-slate-400">
          No se asignó un nivel de desempeño (el admin puede configurarlos más tarde).
        </p>
      )}

      <Link to="/profesor/autoevaluacion">
        <Button variant="secondary" className="mt-2">← Volver a formularios</Button>
      </Link>
    </div>
  )
}

/* ─── Renderizadores por tipo de pregunta ────────────────── */
function QuestionRenderer({ pregunta, value = {}, onChange }) {
  const { tipo, opciones = [], config = {} } = pregunta
  const valorTexto = value.valor_texto ?? ''
  const opcionesSeleccionadas = value.opciones_seleccionadas ?? []

  const setTexto = (v) => onChange({ ...value, valor_texto: v, opciones_seleccionadas: [] })
  const setOpciones = (ids) => onChange({ ...value, valor_texto: '', opciones_seleccionadas: ids })

  switch (tipo) {
    case 'TEXTO_CORTO':
      return (
        <input
          value={valorTexto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Tu respuesta"
          className={inputCls}
        />
      )

    case 'TEXTO_LARGO':
      return (
        <textarea
          value={valorTexto}
          onChange={(e) => setTexto(e.target.value)}
          rows={4}
          placeholder="Tu respuesta"
          className={inputCls}
        />
      )

    case 'OPCION_UNICA':
    case 'LISTA_DESPLEGABLE':
      if (tipo === 'LISTA_DESPLEGABLE') {
        return (
          <select
            value={opcionesSeleccionadas[0] ?? ''}
            onChange={(e) =>
              setOpciones(e.target.value ? [Number(e.target.value)] : [])
            }
            className={inputCls}
          >
            <option value="">-- Selecciona --</option>
            {opciones.map((op) => (
              <option key={op.id} value={op.id}>
                {op.texto}
              </option>
            ))}
          </select>
        )
      }
      return (
        <div className="space-y-2">
          {opciones.map((op) => (
            <label
              key={op.id}
              className={`flex items-center gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                opcionesSeleccionadas.includes(op.id)
                  ? 'border-indigo-400 bg-indigo-50'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <input
                type="radio"
                name={`pregunta-${pregunta.id}`}
                checked={opcionesSeleccionadas.includes(op.id)}
                onChange={() => setOpciones([op.id])}
                className="accent-indigo-600"
              />
              <span className="text-sm text-slate-700">{op.texto}</span>
            </label>
          ))}
        </div>
      )

    case 'CASILLAS':
      return (
        <div className="space-y-2">
          {opciones.map((op) => {
            const checked = opcionesSeleccionadas.includes(op.id)
            return (
              <label
                key={op.id}
                className={`flex items-center gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                  checked
                    ? 'border-indigo-400 bg-indigo-50'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() =>
                    setOpciones(
                      checked
                        ? opcionesSeleccionadas.filter((id) => id !== op.id)
                        : [...opcionesSeleccionadas, op.id]
                    )
                  }
                  className="accent-indigo-600 h-4 w-4"
                />
                <span className="text-sm text-slate-700">{op.texto}</span>
              </label>
            )
          })}
        </div>
      )

    case 'SI_NO': {
      const ops = [
        { id: 'SI', label: 'Sí' },
        { id: 'NO', label: 'No' },
      ]
      return (
        <div className="flex gap-3">
          {ops.map((op) => (
            <label
              key={op.id}
              className={`flex flex-1 items-center justify-center gap-2 rounded-lg border p-3 cursor-pointer transition-colors ${
                valorTexto === op.id
                  ? 'border-indigo-400 bg-indigo-50 font-medium text-indigo-800'
                  : 'border-slate-200 hover:border-slate-300 text-slate-700'
              }`}
            >
              <input
                type="radio"
                name={`pregunta-${pregunta.id}`}
                checked={valorTexto === op.id}
                onChange={() => setTexto(op.id)}
                className="accent-indigo-600"
              />
              {op.label}
            </label>
          ))}
        </div>
      )
    }

    case 'ESCALA_LINEAL': {
      const min = config.min ?? 1
      const max = config.max ?? 5
      const steps = Array.from({ length: max - min + 1 }, (_, i) => min + i)
      const selected = valorTexto ? Number(valorTexto) : null
      return (
        <div>
          <div className="flex gap-2 flex-wrap">
            {steps.map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setTexto(String(v))}
                className={`h-10 w-10 rounded-lg border text-sm font-medium transition-colors ${
                  selected === v
                    ? 'border-indigo-500 bg-indigo-600 text-white'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-indigo-300'
                }`}
              >
                {v}
              </button>
            ))}
          </div>
          <div className="flex justify-between mt-1 text-xs text-slate-400">
            <span>{config.label_min ?? String(min)}</span>
            <span>{config.label_max ?? String(max)}</span>
          </div>
        </div>
      )
    }

    default:
      return <p className="text-sm text-slate-400 italic">Tipo de pregunta desconocido: {tipo}</p>
  }
}

/* ─── Página principal ─────────────────────────────────────── */
export default function AutoevaluacionFormPage() {
  const { id: formularioId } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [answers, setAnswers] = useState({})
  const [respuestaId, setRespuestaId] = useState(null)
  const [enviada, setEnviada] = useState(false)
  const [resultadoFinal, setResultadoFinal] = useState(null)
  const [apiError, setApiError] = useState(null)

  /* ── Cargar formulario ── */
  const { data: formulario, isLoading: loadingForm } = useQuery({
    queryKey: ['formulario-disponible', formularioId],
    queryFn: () => getFormularioDisponible(formularioId).then((r) => r.data),
  })

  /* ── Cargar respuesta borrador si existe ── */
  const { data: respuesta, isLoading: loadingRespuesta } = useQuery({
    queryKey: ['respuesta', formulario?.respuesta_id],
    queryFn: () => getRespuesta(formulario.respuesta_id).then((r) => r.data),
    enabled: Boolean(formulario?.respuesta_id),
  })

  /* ── Pre-llenar respuestas al cargar ── */
  useEffect(() => {
    if (!formulario) return
    setRespuestaId(formulario.respuesta_id ?? null)
    setEnviada(formulario.ya_respondido)
  }, [formulario])

  useEffect(() => {
    if (!respuesta) return
    const init = {}
    ;(respuesta.items || []).forEach((item) => {
      init[item.pregunta] = {
        valor_texto: item.valor_texto || '',
        opciones_seleccionadas: item.opciones_seleccionadas || [],
      }
    })
    setAnswers(init)
    // Si ya fue enviada, guardar el resultado
    if (respuesta.estado === 'ENVIADO') {
      setResultadoFinal(respuesta)
    }
  }, [respuesta])

  /* ── Transformar answers → items API ── */
  const buildItems = useCallback(() => {
    const preguntas = formulario?.preguntas ?? []
    return preguntas.map((p) => {
      const ans = answers[p.id] ?? {}
      return {
        pregunta: p.id,
        valor_texto: ans.valor_texto ?? '',
        opciones_seleccionadas: ans.opciones_seleccionadas ?? [],
      }
    })
  }, [answers, formulario])

  /* ── Guardar borrador ── */
  const saveMut = useMutation({
    mutationFn: async () => {
      const items = buildItems()
      if (!respuestaId) {
        const r = await createRespuesta({ formulario: Number(formularioId), items })
        setRespuestaId(r.data.id)
        return r.data
      }
      return updateRespuesta(respuestaId, { items }).then((r) => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['formularios-disponibles'] })
      qc.invalidateQueries({ queryKey: ['formulario-disponible', formularioId] })
    },
    onError: (e) =>
      setApiError(e.response?.data?.detail || 'Error al guardar el borrador.'),
  })

  /* ── Enviar ── */
  const sendMut = useMutation({
    mutationFn: async () => {
      const items = buildItems()
      let rId = respuestaId
      if (!rId) {
        const created = await createRespuesta({ formulario: Number(formularioId), items })
        rId = created.data.id
        setRespuestaId(rId)
      } else {
        await updateRespuesta(rId, { items })
      }
      return enviarRespuesta(rId).then((r) => r.data)
    },
    onSuccess: (data) => {
      setResultadoFinal(data)
      setEnviada(true)
      qc.invalidateQueries({ queryKey: ['formularios-disponibles'] })
    },
    onError: (e) => {
      const data = e.response?.data
      if (data?.preguntas_faltantes) {
        setApiError(
          `Faltan preguntas obligatorias por responder (IDs: ${data.preguntas_faltantes.join(', ')}).`
        )
      } else {
        setApiError(data?.detail || data?.non_field_errors?.[0] || 'Error al enviar.')
      }
    },
  })

  const updateAnswer = (preguntaId, value) => {
    setAnswers((prev) => ({ ...prev, [preguntaId]: value }))
  }

  /* ── Carga ── */
  if (loadingForm || (formulario?.respuesta_id && loadingRespuesta)) {
    return <Loading text="Cargando formulario..." />
  }

  if (!formulario) {
    return (
      <div className="text-center py-16 text-slate-400">
        Formulario no encontrado.{' '}
        <Link to="/profesor/autoevaluacion" className="text-indigo-600 underline">
          Volver
        </Link>
      </div>
    )
  }

  /* ── Vista: resultado (ya enviado) ── */
  if (enviada && resultadoFinal) {
    return (
      <div className="space-y-6 max-w-xl">
        <div className="flex items-center gap-3">
          <Link to="/profesor/autoevaluacion" className="text-slate-400 hover:text-slate-600">
            ← Volver
          </Link>
          <h1 className="text-xl font-bold text-slate-900">{formulario.titulo}</h1>
        </div>
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 font-medium">
          ✓ Tu autoevaluación ha sido enviada correctamente.
        </div>
        <ResultCard respuesta={resultadoFinal} />
      </div>
    )
  }

  /* ── Vista: resultado ya existente sin datos locales ── */
  if (enviada && !resultadoFinal && respuesta?.estado === 'ENVIADO') {
    return (
      <div className="space-y-6 max-w-xl">
        <div className="flex items-center gap-3">
          <Link to="/profesor/autoevaluacion" className="text-slate-400 hover:text-slate-600">
            ← Volver
          </Link>
          <h1 className="text-xl font-bold text-slate-900">{formulario.titulo}</h1>
        </div>
        <ResultCard respuesta={respuesta} />
      </div>
    )
  }

  /* ── Vista: renderizar preguntas ── */
  const preguntas = formulario.preguntas ?? []

  // Agrupar por sección
  const secciones = formulario.secciones ?? []
  const sinSeccion = preguntas.filter((p) => !p.seccion)

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to="/profesor/autoevaluacion" className="text-slate-400 hover:text-slate-600">
          ← Volver
        </Link>
        <div>
          <h1 className="text-xl font-bold text-slate-900">{formulario.titulo}</h1>
          {formulario.descripcion && (
            <p className="text-sm text-slate-500 mt-0.5">{formulario.descripcion}</p>
          )}
        </div>
      </div>

      {/* Aviso de versión actualizada */}
      {formulario.version > 1 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          ⚠ Este formulario fue actualizado (versión {formulario.version}). Por favor completa la
          nueva versión.
        </div>
      )}

      {apiError && (
        <Alert type="error" onClose={() => setApiError(null)}>
          {apiError}
        </Alert>
      )}

      {/* Preguntas sin sección */}
      {sinSeccion.length > 0 && (
        <div className="space-y-4">
          {sinSeccion.map((p, idx) => (
            <PreguntaCard
              key={p.id}
              pregunta={p}
              numero={idx + 1}
              value={answers[p.id]}
              onChange={(v) => updateAnswer(p.id, v)}
            />
          ))}
        </div>
      )}

      {/* Preguntas por sección */}
      {(() => {
        let globalIdx = sinSeccion.length
        return secciones.map((sec) => {
          const pSec = preguntas.filter((p) => p.seccion === sec.id)
          if (!pSec.length) return null
          const startIdx = globalIdx
          globalIdx += pSec.length
          return (
            <div key={sec.id} className="space-y-4">
              <div className="rounded-xl bg-slate-100 px-4 py-3">
                <h2 className="font-semibold text-slate-800">{sec.titulo}</h2>
                {sec.descripcion && (
                  <p className="text-sm text-slate-500 mt-0.5">{sec.descripcion}</p>
                )}
              </div>
              {pSec.map((p, idx) => (
                <PreguntaCard
                  key={p.id}
                  pregunta={p}
                  numero={startIdx + idx + 1}
                  value={answers[p.id]}
                  onChange={(v) => updateAnswer(p.id, v)}
                />
              ))}
            </div>
          )
        })
      })()}

      {/* Footer con acciones */}
      <div className="flex justify-between gap-3 pb-8 pt-2 border-t border-slate-200">
        <Button
          variant="secondary"
          onClick={() => saveMut.mutate()}
          loading={saveMut.isPending}
        >
          Guardar borrador
        </Button>
        <Button
          onClick={() => sendMut.mutate()}
          loading={sendMut.isPending}
        >
          Enviar autoevaluación
        </Button>
      </div>
    </div>
  )
}

/* ─── Tarjeta de una sola pregunta ───────────────────────── */
function PreguntaCard({ pregunta, numero, value, onChange }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
          {numero}
        </span>
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-900">
            {pregunta.texto}
            {pregunta.obligatoria && (
              <span className="ml-1 text-rose-500">*</span>
            )}
          </p>
          {pregunta.ayuda && (
            <p className="mt-0.5 text-xs text-slate-400">{pregunta.ayuda}</p>
          )}
        </div>
      </div>
      <QuestionRenderer
        pregunta={pregunta}
        value={value}
        onChange={onChange}
      />
    </div>
  )
}
