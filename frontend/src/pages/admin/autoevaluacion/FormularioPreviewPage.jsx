/**
 * Vista previa del Formulario de Autoevaluación para el admin.
 *
 * Muestra el formulario exactamente como lo verá el profesor: encabezado +
 * preguntas renderizadas por tipo. Las preguntas se renderizan como inputs
 * deshabilitados — el admin no envía nada, solo confirma cómo lucirá.
 *
 * Barra superior con acciones: Editar y Eliminar (despublican primero si
 * hace falta), y "Ver disponible para profesores" si está publicado.
 */
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteFormulario,
  despublicarFormulario,
  getFormulario,
  getNivelesDesempeno,
} from '../../../api/autoevaluacion'
import Alert from '../../../components/ui/Alert'
import Badge from '../../../components/ui/Badge'
import Button from '../../../components/ui/Button'
import Loading from '../../../components/ui/Loading'
import { inputCls } from '../../../components/ui/FormField'

/* ─── Render de cada pregunta (sólo lectura) ──────────────────────────── */
function QuestionPreview({ pregunta }) {
  const { tipo, opciones = [], filas = [], config = {} } = pregunta

  switch (tipo) {
    case 'TEXTO_CORTO':
      return <input disabled placeholder="(respuesta corta del profesor)" className={inputCls + ' bg-slate-50'} />
    case 'TEXTO_LARGO':
      return <textarea disabled rows={4} placeholder="(respuesta larga del profesor)" className={inputCls + ' bg-slate-50'} />
    case 'LISTA_DESPLEGABLE':
      return (
        <select disabled className={inputCls + ' bg-slate-50'}>
          <option>-- Selecciona --</option>
          {opciones.map((op) => <option key={op.id}>{op.texto}</option>)}
        </select>
      )
    case 'OPCION_UNICA':
      return (
        <div className="space-y-2">
          {opciones.map((op) => (
            <label key={op.id} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
              <input type="radio" disabled className="accent-indigo-600" />
              <span className="text-sm text-slate-700">{op.texto}</span>
              {op.puntos > 0 && (
                <span className="ml-auto text-xs text-slate-400">{op.puntos} pts</span>
              )}
            </label>
          ))}
        </div>
      )
    case 'CASILLAS':
      return (
        <div className="space-y-2">
          {opciones.map((op) => (
            <label key={op.id} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
              <input type="checkbox" disabled className="accent-indigo-600 h-4 w-4" />
              <span className="text-sm text-slate-700">{op.texto}</span>
              {op.puntos > 0 && (
                <span className="ml-auto text-xs text-slate-400">+{op.puntos} pts</span>
              )}
            </label>
          ))}
        </div>
      )
    case 'SI_NO':
      return (
        <div className="flex gap-3">
          {['Sí', 'No'].map((label) => (
            <label key={label} className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
              <input type="radio" disabled className="accent-indigo-600" />
              <span className="text-sm text-slate-700">{label}</span>
            </label>
          ))}
        </div>
      )
    case 'ESCALA_LINEAL': {
      const min = config.min ?? 1
      const max = config.max ?? 5
      const steps = Array.from({ length: max - min + 1 }, (_, i) => min + i)
      return (
        <div>
          <div className="flex gap-2 flex-wrap">
            {steps.map((v) => (
              <button
                key={v}
                type="button"
                disabled
                className="h-10 w-10 rounded-lg border border-slate-200 bg-slate-50 text-sm font-medium text-slate-600"
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
    case 'CUADRICULA': {
      const cols = opciones
      if (!filas.length || !cols.length) {
        return <p className="text-sm text-slate-400 italic">Cuadrícula sin filas o columnas definidas.</p>
      }
      return (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr>
                <th className="border border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs font-medium text-slate-500 w-1/3" />
                {cols.map((col) => (
                  <th key={col.id} className="border border-slate-200 bg-slate-50 px-3 py-2 text-center text-xs font-medium text-slate-700">
                    {col.texto}
                    {col.puntos > 0 && <span className="block text-slate-400">{col.puntos} pts</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filas.map((fila) => (
                <tr key={fila.id} className="even:bg-slate-50">
                  <td className="border border-slate-200 px-3 py-2 text-slate-700">{fila.texto}</td>
                  {cols.map((col) => (
                    <td key={col.id} className="border border-slate-200 px-3 py-2 text-center">
                      <input type="radio" disabled className="accent-indigo-600" />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }
    default:
      return <p className="text-sm text-slate-400 italic">Tipo desconocido: {tipo}</p>
  }
}

function PreguntaCard({ pregunta, numero }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
          {numero}
        </span>
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-900">
            {pregunta.texto}
            {pregunta.obligatoria && <span className="ml-1 text-rose-500">*</span>}
          </p>
          {pregunta.ayuda && (
            <p className="mt-0.5 text-xs text-slate-400">{pregunta.ayuda}</p>
          )}
        </div>
      </div>
      <QuestionPreview pregunta={pregunta} />
    </div>
  )
}

/* ─── Página principal ───────────────────────────────────────────────── */
export default function FormularioPreviewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [apiError, setApiError] = useState(null)

  const { data: formulario, isLoading } = useQuery({
    queryKey: ['formulario', id],
    queryFn: () => getFormulario(id).then((r) => r.data),
  })
  const { data: niveles = [] } = useQuery({
    queryKey: ['niveles', id],
    queryFn: () =>
      getNivelesDesempeno({ formulario: id }).then((r) => r.data?.results ?? r.data ?? []),
  })

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['formulario', id] })
    qc.invalidateQueries({ queryKey: ['formularios'] })
  }
  const onError = (e) => setApiError(
    e.response?.data?.detail
    || e.response?.data?.non_field_errors?.[0]
    || 'Error.'
  )

  const editMut = useMutation({
    mutationFn: async () => {
      if (formulario?.estado === 'PUBLICADO' || formulario?.estado === 'CERRADO') {
        await despublicarFormulario(id)
      }
    },
    onSuccess: () => {
      invalidate()
      navigate(`/admin/autoevaluacion/${id}`)
    },
    onError,
  })

  const deleteMut = useMutation({
    mutationFn: async () => {
      if (formulario?.estado === 'PUBLICADO' || formulario?.estado === 'CERRADO') {
        await despublicarFormulario(id)
      }
      return deleteFormulario(id)
    },
    onSuccess: () => {
      invalidate()
      navigate('/admin/autoevaluacion')
    },
    onError,
  })

  const onEditClick = () => {
    const estado = formulario?.estado
    if (estado === 'PUBLICADO' || estado === 'CERRADO') {
      if (!window.confirm(
        `Este formulario está ${estado}. Para editarlo se cerrará primero ` +
        '(dejará de aparecer para los profesores). ¿Continuar?'
      )) return
    }
    editMut.mutate()
  }
  const onDeleteClick = () => {
    const total = formulario?.total_respuestas ?? 0
    const aviso = total > 0
      ? `Este formulario tiene ${total} respuesta(s) registradas. Si lo eliminas, se borrará el historial. ¿Continuar?`
      : '¿Eliminar este formulario?'
    if (window.confirm(aviso)) deleteMut.mutate()
  }

  if (isLoading) return <Loading text="Cargando vista previa..." />
  if (!formulario) {
    return (
      <div className="p-8">
        <p className="text-sm text-slate-500">No se pudo cargar el formulario.</p>
        <Link to="/admin/autoevaluacion" className="text-indigo-600 text-sm hover:underline">
          ← Volver
        </Link>
      </div>
    )
  }

  const preguntas = formulario.preguntas ?? []
  const secciones = formulario.secciones ?? []
  const sinSeccion = preguntas.filter((p) => !p.seccion)
  const isPublicado = formulario.estado === 'PUBLICADO'

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      {/* Barra superior de acciones */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 flex items-center gap-3 flex-wrap">
        <Link to="/admin/autoevaluacion" className="text-sm text-slate-500 hover:text-slate-700">
          ← Formularios
        </Link>
        <span className="text-xs text-slate-300">|</span>
        <Badge label={formulario.estado} variant={formulario.estado} />
        {isPublicado ? (
          <span className="text-xs text-emerald-600">● Visible para profesores.</span>
        ) : (
          <span className="text-xs text-slate-500">Solo tú puedes verlo (Borrador).</span>
        )}

        <div className="ml-auto flex gap-2 flex-wrap">
          <Button
            size="sm"
            variant="secondary"
            loading={editMut.isPending}
            onClick={onEditClick}
          >
            Editar
          </Button>
          <Button
            size="sm"
            variant="danger"
            loading={deleteMut.isPending}
            onClick={onDeleteClick}
          >
            Eliminar
          </Button>
        </div>
      </div>

      {apiError && (
        <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>
      )}

      {/* Tarjeta tipo "encabezado del formulario que verá el profesor" */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <p className="text-xs uppercase tracking-widest text-indigo-600 font-semibold">
          Autoevaluación
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">{formulario.titulo}</h1>
        {formulario.descripcion && (
          <p className="text-sm text-slate-500 mt-2">{formulario.descripcion}</p>
        )}
        <p className="text-xs text-slate-400 mt-3">
          Periodo: {formulario.periodo_clave} · {preguntas.length} preguntas
          {formulario.puntaje_maximo_posible != null && (
            <>{' '}· Puntaje máximo: {Number(formulario.puntaje_maximo_posible).toFixed(1)} pts</>
          )}
        </p>
      </div>

      {/* Preguntas — sin sección */}
      {sinSeccion.length > 0 && (
        <div className="space-y-4">
          {sinSeccion.map((p, idx) => (
            <PreguntaCard key={p.id} pregunta={p} numero={idx + 1} />
          ))}
        </div>
      )}

      {/* Preguntas por sección */}
      {secciones.map((sec) => {
        const pSec = preguntas.filter((p) => p.seccion === sec.id)
        if (!pSec.length) return null
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
                numero={sinSeccion.length + idx + 1}
              />
            ))}
          </div>
        )
      })}

      {preguntas.length === 0 && (
        <p className="text-center text-sm text-slate-400 italic py-12">
          Sin preguntas. Vuelve al editor para agregar la primera.
        </p>
      )}

      {/* Niveles de desempeño — solo lectura, así el admin ve qué observación
          recibirá el profesor según el puntaje obtenido */}
      {niveles.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-3">
          <h2 className="text-sm font-semibold text-slate-800">
            Niveles de desempeño (lo que verá el profesor al enviar)
          </h2>
          <div className="space-y-2">
            {niveles.map((n) => {
              const bg = { green: 'bg-emerald-50 border-emerald-200', blue: 'bg-blue-50 border-blue-200', yellow: 'bg-amber-50 border-amber-200', red: 'bg-rose-50 border-rose-200', gray: 'bg-slate-50 border-slate-200' }
              return (
                <div key={n.id} className={`rounded-lg border p-3 ${bg[n.color] ?? bg.gray}`}>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-800 text-sm">{n.nombre}</span>
                    <span className="text-xs text-slate-500">{n.porcentaje_min}% – {n.porcentaje_max}%</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">{n.observacion}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
