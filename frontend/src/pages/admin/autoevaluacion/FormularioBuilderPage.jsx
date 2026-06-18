/**
 * Form Builder — Admin.
 * Edita secciones (con peso ponderado), preguntas, opciones, niveles y acciones de estado.
 * Tabs: Preguntas | Niveles | Estadísticas
 */
import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getFormulario,
  publicarFormulario, despublicarFormulario, reabrirFormulario,
  createPregunta, updatePregunta, patchPregunta, deletePregunta,
  createSeccion, updateSeccion, deleteSeccion,
  getNivelesDesempeno, createNivelDesempeno, updateNivelDesempeno, deleteNivelDesempeno,
  getFormularioEstadisticas,
} from '../../../api/autoevaluacion'
import Button from '../../../components/ui/Button'
import Badge from '../../../components/ui/Badge'
import Alert from '../../../components/ui/Alert'
import Modal from '../../../components/ui/Modal'
import Loading from '../../../components/ui/Loading'
import FormField, { inputCls } from '../../../components/ui/FormField'

/* ─── Constantes ──────────────────────────────────────────── */
const TIPOS = [
  { value: 'OPCION_UNICA',      label: 'Opción única' },
  { value: 'CASILLAS',          label: 'Casillas de verificación' },
  { value: 'LISTA_DESPLEGABLE', label: 'Lista desplegable' },
  { value: 'SI_NO',             label: 'Sí / No' },
  { value: 'ESCALA_LINEAL',     label: 'Escala lineal' },
  { value: 'CUADRICULA',        label: 'Cuadrícula de opciones' },
  { value: 'TEXTO_CORTO',       label: 'Texto corto' },
  { value: 'TEXTO_LARGO',       label: 'Texto largo' },
]
const TIPOS_CON_OPCIONES = ['OPCION_UNICA', 'CASILLAS', 'LISTA_DESPLEGABLE']
const NIVEL_COLORES = ['green', 'blue', 'yellow', 'red', 'gray']

const emptyPregunta = (orden = 1, seccion = null) => ({
  tipo: 'OPCION_UNICA', texto: '', ayuda: '', obligatoria: true, orden,
  config: {}, opciones: [], filas: [], seccion,
})
const emptyNivel = (orden = 0) => ({
  nombre: '', porcentaje_min: '', porcentaje_max: '', observacion: '', color: 'gray', orden,
})
const emptySeccion = (orden = 0) => ({
  titulo: '', descripcion: '', peso: '0', orden,
})

/* ─── OpcionesEditor ──────────────────────────────────────── */
const inputBase = 'rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500'

function OpcionesEditor({ opciones, onChange }) {
  const add = () => onChange([...opciones, { texto: '', valor: '', puntos: 0, orden: opciones.length + 1 }])
  const remove = (i) => onChange(opciones.filter((_, idx) => idx !== i))
  const update = (i, key, val) => onChange(opciones.map((op, idx) => idx === i ? { ...op, [key]: val } : op))
  return (
    <div className="space-y-2">
      {opciones.map((op, i) => (
        <div key={i} className="flex gap-2 items-center">
          <input value={op.texto} onChange={(e) => update(i, 'texto', e.target.value)}
            placeholder="Texto de la opción" className={`${inputBase} min-w-0 flex-1`} />
          <input type="number" step="0.5" min={0} value={op.puntos}
            onChange={(e) => update(i, 'puntos', Number(e.target.value))}
            className={`${inputBase} w-20 shrink-0 text-center`} />
          <span className="shrink-0 text-xs text-slate-400">pts</span>
          <button type="button" onClick={() => remove(i)} className="shrink-0 text-slate-400 hover:text-rose-500">×</button>
        </div>
      ))}
      <button type="button" onClick={add} className="text-xs text-indigo-600 hover:underline">+ Añadir opción</button>
    </div>
  )
}

/* ─── FilasEditor ────────────────────────────────────────── */
function FilasEditor({ filas, onChange }) {
  const add = () => onChange([...filas, { texto: '', orden: filas.length + 1 }])
  const remove = (i) => onChange(filas.filter((_, idx) => idx !== i))
  const update = (i, val) => onChange(filas.map((f, idx) => idx === i ? { ...f, texto: val } : f))
  return (
    <div className="space-y-2">
      {filas.map((f, i) => (
        <div key={i} className="flex gap-2 items-center">
          <span className="shrink-0 text-xs text-slate-400 w-5 text-right">{i + 1}.</span>
          <input value={f.texto} onChange={(e) => update(i, e.target.value)}
            placeholder="Texto de la fila" className={`${inputBase} min-w-0 flex-1`} />
          <button type="button" onClick={() => remove(i)} className="shrink-0 text-slate-400 hover:text-rose-500">×</button>
        </div>
      ))}
      <button type="button" onClick={add} className="text-xs text-indigo-600 hover:underline">+ Añadir fila</button>
    </div>
  )
}

/* ─── PreguntaModal ───────────────────────────────────────── */
function PreguntaModal({ onClose, initial, onSave, loading, secciones = [] }) {
  const [q, setQ] = useState(initial ?? emptyPregunta())
  const f  = (key) => (e) => setQ((p) => ({ ...p, [key]: e.target.value }))
  const fc = (key) => (e) => setQ((p) => ({ ...p, config: { ...p.config, [key]: e.target.value } }))

  const tieneOpciones = TIPOS_CON_OPCIONES.includes(q.tipo)
  const esSiNo      = q.tipo === 'SI_NO'
  const esEscala    = q.tipo === 'ESCALA_LINEAL'
  const esCuadricula = q.tipo === 'CUADRICULA'

  return (
    <Modal open onClose={onClose} size="2xl"
      title={initial?.id ? 'Editar Pregunta' : 'Nueva Pregunta'}
      footer={<>
        <Button variant="secondary" onClick={onClose}>Cancelar</Button>
        <Button loading={loading} onClick={() => onSave(q)}>Guardar pregunta</Button>
      </>}>
      <div className="space-y-4">
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <FormField label="Tipo">
              <select value={q.tipo}
                onChange={(e) => setQ((p) => ({ ...p, tipo: e.target.value, opciones: [], filas: [], config: {} }))}
                className={inputCls}>
                {TIPOS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </FormField>
          </div>
          <label className="flex items-center gap-2 cursor-pointer mb-2 shrink-0">
            <input type="checkbox" checked={q.obligatoria} onChange={(e) => setQ((p) => ({ ...p, obligatoria: e.target.checked }))} className="h-4 w-4 accent-indigo-600" />
            <span className="text-sm text-slate-700">Obligatoria</span>
          </label>
        </div>

        {secciones.length > 0 && (
          <FormField label="Sección">
            <select value={q.seccion ?? ''} onChange={(e) => setQ((p) => ({ ...p, seccion: e.target.value ? Number(e.target.value) : null }))} className={inputCls}>
              <option value="">Sin sección</option>
              {secciones.map((s) => <option key={s.id} value={s.id}>{s.titulo}</option>)}
            </select>
          </FormField>
        )}

        <FormField label="Texto de la pregunta" required>
          <textarea value={q.texto} onChange={f('texto')} rows={2} className={inputCls} placeholder="Escribe la pregunta aquí" />
        </FormField>
        <FormField label="Texto de ayuda (opcional)">
          <input value={q.ayuda} onChange={f('ayuda')} className={inputCls} placeholder="Instrucción breve para el profesor" />
        </FormField>

        {tieneOpciones && (
          <div>
            <p className="text-sm font-medium text-slate-700 mb-2">Opciones <span className="text-xs text-slate-400">(texto + puntos que suma cada opción)</span></p>
            <OpcionesEditor opciones={q.opciones ?? []} onChange={(ops) => setQ((p) => ({ ...p, opciones: ops }))} />
          </div>
        )}

        {esCuadricula && (
          <div className="grid grid-cols-2 gap-6 rounded-xl border border-indigo-100 bg-indigo-50/40 p-4">
            <div>
              <p className="text-sm font-medium text-slate-700 mb-2">
                Filas <span className="text-xs text-slate-400">(enunciados a evaluar)</span>
              </p>
              <FilasEditor filas={q.filas ?? []} onChange={(fs) => setQ((p) => ({ ...p, filas: fs }))} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-700 mb-2">
                Columnas <span className="text-xs text-slate-400">(opciones de respuesta + puntos)</span>
              </p>
              <OpcionesEditor opciones={q.opciones ?? []} onChange={(ops) => setQ((p) => ({ ...p, opciones: ops }))} />
            </div>
          </div>
        )}

        {esSiNo && (
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Puntos si responde Sí">
              <input type="number" step="0.5" min={0} value={q.config.puntos_si ?? 1} onChange={fc('puntos_si')} className={inputCls} />
            </FormField>
            <FormField label="Puntos si responde No">
              <input type="number" step="0.5" min={0} value={q.config.puntos_no ?? 0} onChange={fc('puntos_no')} className={inputCls} />
            </FormField>
          </div>
        )}

        {esEscala && (
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Valor mínimo"><input type="number" value={q.config.min ?? 1} onChange={fc('min')} className={inputCls} /></FormField>
            <FormField label="Valor máximo"><input type="number" value={q.config.max ?? 5} onChange={fc('max')} className={inputCls} /></FormField>
            <FormField label="Etiqueta mínimo"><input value={q.config.label_min ?? ''} onChange={fc('label_min')} className={inputCls} placeholder="ej. Nada" /></FormField>
            <FormField label="Etiqueta máximo"><input value={q.config.label_max ?? ''} onChange={fc('label_max')} className={inputCls} placeholder="ej. Totalmente" /></FormField>
            <div className="col-span-2">
              <FormField label="Factor de puntos" hint="Score = valor_seleccionado × factor (ej. escala 1-5 × 2 = máx 10 pts)">
                <input type="number" step="0.5" min={0} value={q.config.puntos_factor ?? 1} onChange={fc('puntos_factor')} className={inputCls + ' w-24'} />
              </FormField>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}

/* ─── PreguntaRow ─────────────────────────────────────────── */
function PreguntaRow({ p, idx, secciones, editable, onEdit, onDelete, onMover }) {
  const tipoLabel = TIPOS.find((t) => t.value === p.tipo)?.label ?? p.tipo
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-3 flex items-start gap-3">
      <span className="shrink-0 mt-0.5 rounded-full bg-slate-200 px-2 py-0.5 text-xs font-semibold text-slate-600">{idx + 1}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs rounded bg-indigo-50 text-indigo-700 px-2 py-0.5 font-medium">{tipoLabel}</span>
          {p.obligatoria && <span className="text-xs text-rose-500">*obligatoria</span>}
        </div>
        <p className="text-sm text-slate-800">{p.texto}</p>
        {p.tipo === 'CUADRICULA' && (
          <p className="text-xs text-slate-500 mt-1">
            {p.filas?.length ?? 0} filas × {p.opciones?.length ?? 0} columnas
          </p>
        )}
        {p.tipo !== 'CUADRICULA' && p.opciones?.length > 0 && (
          <ul className="mt-1 space-y-0.5">
            {p.opciones.map((op) => (
              <li key={op.id} className="text-xs text-slate-500">· {op.texto} <span className="text-slate-400">({op.puntos} pts)</span></li>
            ))}
          </ul>
        )}
        {p.tipo === 'ESCALA_LINEAL' && p.config?.max && (
          <p className="text-xs text-slate-400 mt-1">Escala {p.config.min ?? 1}–{p.config.max} × {p.config.puntos_factor ?? 1} factor</p>
        )}
      </div>
      {editable && (
        <div className="flex items-center gap-2 shrink-0">
          {secciones.length > 1 && (
            <select
              value={p.seccion ?? ''}
              onChange={(e) => onMover(p, e.target.value ? Number(e.target.value) : null)}
              className="text-xs border border-slate-200 rounded px-1.5 py-1 bg-white text-slate-600"
            >
              <option value="">Sin sección</option>
              {secciones.map((s) => <option key={s.id} value={s.id}>{s.titulo}</option>)}
            </select>
          )}
          <Button size="sm" variant="secondary" onClick={() => onEdit(p)}>Editar</Button>
          <Button size="sm" variant="danger" onClick={() => window.confirm('¿Eliminar esta pregunta?') && onDelete(p.id)}>×</Button>
        </div>
      )}
    </div>
  )
}

/* ─── SeccionCard ─────────────────────────────────────────── */
function SeccionCard({ s, editable, secciones, onEdit, onDelete, onAddPregunta, onEditPregunta, onDeletePregunta, onMoverPregunta, onUpdatePeso }) {
  const [localPeso, setLocalPeso] = useState(String(s.peso ?? '0'))
  useEffect(() => { setLocalPeso(String(s.peso ?? '0')) }, [s.peso])

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      {/* Header de la sección */}
      <div className="flex items-center gap-3 p-4 border-b border-slate-100">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-800">{s.titulo}</p>
          {s.descripcion && <p className="text-xs text-slate-500 mt-0.5">{s.descripcion}</p>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-slate-500">Peso:</span>
          <input
            type="number" min={0} max={100} step={0.01}
            value={localPeso}
            onChange={(e) => setLocalPeso(e.target.value)}
            onBlur={() => { if (Number(localPeso) !== Number(s.peso)) onUpdatePeso(s.id, localPeso) }}
            className="w-20 text-center text-sm border border-slate-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-400 disabled:bg-slate-50 disabled:text-slate-400"
            disabled={!editable}
          />
          <span className="text-xs text-slate-500">%</span>
          {editable && (
            <>
              <Button size="sm" variant="secondary" onClick={onEdit}>Editar</Button>
              <Button size="sm" variant="danger" onClick={onDelete}>×</Button>
            </>
          )}
        </div>
      </div>

      {/* Preguntas de la sección */}
      <div className="p-4 space-y-2">
        {s.preguntas.length === 0 && (
          <p className="text-xs text-slate-400 italic">Sin preguntas en esta sección.</p>
        )}
        {s.preguntas.map((p, idx) => (
          <PreguntaRow
            key={p.id} p={p} idx={idx} secciones={secciones} editable={editable}
            onEdit={onEditPregunta}
            onDelete={onDeletePregunta}
            onMover={onMoverPregunta}
          />
        ))}
        {editable && (
          <div className="pt-1">
            <Button size="sm" variant="secondary" onClick={() => onAddPregunta(s.id)}>
              + Añadir pregunta
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── Página principal ─────────────────────────────────────── */
export default function FormularioBuilderPage() {
  const { id } = useParams()
  const qc = useQueryClient()
  const [tab, setTab] = useState('preguntas')
  const [apiError, setApiError] = useState(null)

  // Pregunta
  const [qModal, setQModal] = useState(false)
  const [editingQ, setEditingQ] = useState(null)

  // Sección
  const [sModal, setSModal] = useState(false)
  const [editingS, setEditingS] = useState(null)
  const [sForm, setSForm] = useState(emptySeccion())

  // Nivel
  const [nModal, setNModal] = useState(false)
  const [editingN, setEditingN] = useState(null)
  const [nForm, setNForm] = useState(emptyNivel())

  /* ── Datos ── */
  const { data: formulario, isLoading } = useQuery({
    queryKey: ['formulario', id],
    queryFn: () => getFormulario(id).then((r) => r.data),
  })
  const { data: niveles = [] } = useQuery({
    queryKey: ['niveles', id],
    queryFn: () => getNivelesDesempeno({ formulario: id }).then((r) => r.data?.results ?? r.data ?? []),
  })
  const { data: stats } = useQuery({
    queryKey: ['stats', id],
    queryFn: () => getFormularioEstadisticas(id).then((r) => r.data),
    enabled: tab === 'estadisticas',
  })

  const invalidateFormulario = () => qc.invalidateQueries({ queryKey: ['formulario', id] })
  const invalidateAll = () => {
    invalidateFormulario()
    qc.invalidateQueries({ queryKey: ['formularios'] })
  }

  /* ── Acciones de estado ── */
  const pubMut = useMutation({
    mutationFn: () => publicarFormulario(id),
    onSuccess: invalidateAll,
    onError: (e) => {
      const d = e.response?.data || {}
      setApiError(d.detail || d.non_field_errors?.[0] || 'Error al publicar.')
    },
  })
  const desMut = useMutation({
    mutationFn: () => despublicarFormulario(id),
    onSuccess: invalidateAll,
    onError: (e) => setApiError(e.response?.data?.detail || 'Error al cerrar el formulario.'),
  })
  const reaMut = useMutation({
    mutationFn: () => reabrirFormulario(id),
    onSuccess: invalidateAll,
    onError: (e) => setApiError(e.response?.data?.detail || 'Error al reabrir.'),
  })

  /* ── Secciones ── */
  const saveSeccionMut = useMutation({
    mutationFn: (d) => {
      if (d.id) return updateSeccion(d.id, { titulo: d.titulo, descripcion: d.descripcion || '' })
      return createSeccion({ formulario: Number(id), titulo: d.titulo, descripcion: d.descripcion || '', peso: Number(d.peso) || 0, orden: d.orden || 0 })
    },
    onSuccess: () => { invalidateFormulario(); setSModal(false) },
    onError: (e) => setApiError(e.response?.data?.detail || 'Error al guardar sección.'),
  })
  const updatePesoMut = useMutation({
    mutationFn: ({ sId, peso }) => updateSeccion(sId, { peso }),
    onSuccess: invalidateFormulario,
    onError: () => setApiError('Error al guardar el peso.'),
  })
  const deleteSeccionMut = useMutation({
    mutationFn: (sid) => deleteSeccion(sid),
    onSuccess: invalidateFormulario,
    onError: (e) => setApiError(e.response?.data?.detail || 'No se pudo eliminar la sección.'),
  })

  const openNewSeccion = () => {
    setEditingS(null)
    setSForm(emptySeccion(secciones.length))
    setSModal(true)
  }
  const openEditSeccion = (s) => {
    setEditingS(s)
    setSForm({ titulo: s.titulo, descripcion: s.descripcion || '' })
    setSModal(true)
  }
  const handleDeleteSeccion = (s) => {
    if (window.confirm(`¿Eliminar la sección "${s.titulo}"? Las preguntas quedarán sin sección asignada.`)) {
      deleteSeccionMut.mutate(s.id)
    }
  }

  /* ── Preguntas ── */
  const savePreguntaMut = useMutation({
    mutationFn: (q) => {
      const payload = {
        formulario: Number(id), tipo: q.tipo, texto: q.texto,
        ayuda: q.ayuda || '', obligatoria: q.obligatoria,
        orden: Number(q.orden) || 1, config: q.config || {},
        seccion: q.seccion || null,
        opciones: (q.opciones || []).map((op, i) => ({
          texto: op.texto, valor: op.valor || '', puntos: Number(op.puntos) || 0, orden: i + 1,
        })),
        filas: (q.filas || []).map((f, i) => ({
          texto: f.texto, orden: i + 1,
        })),
      }
      return q.id ? updatePregunta(q.id, payload) : createPregunta(payload)
    },
    onSuccess: () => { invalidateFormulario(); setQModal(false) },
    onError: (e) => setApiError(e.response?.data?.non_field_errors?.[0] || e.response?.data?.detail || 'Error al guardar pregunta.'),
  })
  const moverPreguntaMut = useMutation({
    mutationFn: ({ preguntaId, seccionId }) => patchPregunta(preguntaId, { seccion: seccionId }),
    onSuccess: invalidateFormulario,
    onError: () => setApiError('Error al mover la pregunta.'),
  })
  const delPreguntaMut = useMutation({
    mutationFn: (pid) => deletePregunta(pid),
    onSuccess: invalidateFormulario,
    onError: () => setApiError('Error al eliminar pregunta.'),
  })

  const openNewPregunta = (seccionId = null) => {
    setEditingQ(emptyPregunta((formulario?.preguntas?.length ?? 0) + 1, seccionId))
    setQModal(true)
  }
  const openEditPregunta = (p) => {
    setEditingQ({ ...p, opciones: p.opciones ?? [], filas: p.filas ?? [] })
    setQModal(true)
  }

  /* ── Niveles ── */
  const saveNivelMut = useMutation({
    mutationFn: (d) => {
      const payload = { ...d, formulario: Number(id) }
      return d.id ? updateNivelDesempeno(d.id, payload) : createNivelDesempeno(payload)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['niveles', id] }); setNModal(false) },
    onError: (e) => setApiError(e.response?.data?.detail || e.response?.data?.[0] || 'Error al guardar nivel.'),
  })
  const delNivelMut = useMutation({
    mutationFn: (nid) => deleteNivelDesempeno(nid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['niveles', id] }),
  })
  const openNewNivel = () => { setEditingN(null); setNForm(emptyNivel(niveles.length)); setNModal(true) }
  const openEditNivel = (n) => {
    setEditingN(n)
    setNForm({ nombre: n.nombre, porcentaje_min: n.porcentaje_min, porcentaje_max: n.porcentaje_max, observacion: n.observacion, color: n.color, orden: n.orden })
    setNModal(true)
  }

  /* ── Derivados ── */
  const isPublicado = formulario?.estado === 'PUBLICADO'
  const isCerrado   = formulario?.estado === 'CERRADO'
  const isBorrador  = formulario?.estado === 'BORRADOR'
  const editable    = isBorrador

  if (isLoading) return <Loading text="Cargando formulario..." />

  const secciones       = formulario?.secciones ?? []
  const todasPreguntas  = formulario?.preguntas ?? []
  const tieneSecciones  = secciones.length > 0
  const orphans         = tieneSecciones ? todasPreguntas.filter((p) => !p.seccion) : []

  const sumPesos = secciones.reduce((acc, s) => acc + parseFloat(s.peso || 0), 0)
  const pesosOk  = Math.abs(sumPesos - 100) < 0.01

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 flex-wrap">
          <Link to="/admin/autoevaluacion" className="text-slate-400 hover:text-slate-600 text-sm">← Volver</Link>
          <h1 className="text-xl font-bold text-slate-900">{formulario?.titulo}</h1>
          <Badge label={formulario?.estado} variant={formulario?.estado} />
          <span className="text-xs text-slate-400">{formulario?.periodo_clave}</span>
        </div>
        <div className="flex gap-2 shrink-0 flex-wrap">
          <Link to={`/admin/autoevaluacion/${id}/preview`}>
            <Button variant="secondary">Vista previa</Button>
          </Link>
          {isBorrador && (
            <Button onClick={() => pubMut.mutate()} loading={pubMut.isPending}
              title="Publicar para que sea visible y abierto a respuestas">
              Publicar
            </Button>
          )}
          {isPublicado && (
            <Button variant="secondary" loading={desMut.isPending}
              onClick={() => window.confirm('Al cerrar, los profesores dejarán de poder enviarlo y volverá a Borrador. ¿Continuar?') && desMut.mutate()}>
              Cerrar
            </Button>
          )}
          {isCerrado && (
            <>
              <Button loading={reaMut.isPending}
                onClick={() => window.confirm('¿Volver a aceptar respuestas?') && reaMut.mutate()}>
                Reabrir
              </Button>
              <Button variant="secondary" loading={desMut.isPending}
                onClick={() => window.confirm('El formulario regresará a Borrador para que puedas editarlo. ¿Continuar?') && desMut.mutate()}>
                Editar (Borrador)
              </Button>
            </>
          )}
        </div>
      </div>

      {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}

      {formulario?.descripcion && <p className="text-sm text-slate-500">{formulario.descripcion}</p>}
      <div className="flex gap-6 text-sm text-slate-500">
        <span>📋 {todasPreguntas.length} preguntas</span>
        <span>💯 Puntaje máximo: <strong>{formulario?.puntaje_maximo_posible?.toFixed(1) ?? '—'} pts</strong></span>
        <span>✉ {formulario?.total_respuestas} respuestas</span>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 flex gap-1">
        {['preguntas', 'niveles', 'estadisticas'].map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${tab === t ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
            {t === 'preguntas' ? 'Preguntas' : t === 'niveles' ? 'Niveles de Desempeño' : 'Estadísticas'}
          </button>
        ))}
      </div>

      {/* ── Tab: Preguntas ── */}
      {tab === 'preguntas' && (
        <div className="space-y-4">
          {isPublicado && (
            <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-2 text-sm text-amber-800">
              El formulario está <strong>PUBLICADO</strong> y aceptando respuestas. Para modificar
              su estructura ciérralo primero (regresará a Borrador).
            </div>
          )}
          {isCerrado && (
            <div className="rounded-lg bg-slate-50 border border-slate-200 px-4 py-2 text-sm text-slate-700">
              El formulario está <strong>CERRADO</strong>. Usa <em>Reabrir</em> para volver a aceptar
              respuestas, o <em>Editar (Borrador)</em> para modificar su estructura.
            </div>
          )}

          {/* Barra superior: badge de pesos + botón añadir sección */}
          <div className="flex items-center gap-4 flex-wrap">
            {tieneSecciones && (
              <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${pesosOk ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                {pesosOk ? '✓' : '⚠'} Σ pesos = {sumPesos.toFixed(1)}%{!pesosOk && ' — debe ser 100 para publicar'}
              </span>
            )}
            {editable && (
              <Button variant="secondary" className="ml-auto" onClick={openNewSeccion}>
                + Añadir sección
              </Button>
            )}
          </div>

          {/* Sin secciones: lista plana (compatibilidad previa) */}
          {!tieneSecciones && (
            <div className="space-y-3">
              {todasPreguntas.length === 0 && (
                <p className="text-sm text-slate-400 italic">Sin secciones ni preguntas. Empieza añadiendo una sección.</p>
              )}
              {todasPreguntas.map((p, idx) => (
                <PreguntaRow
                  key={p.id} p={p} idx={idx} secciones={[]} editable={editable}
                  onEdit={openEditPregunta}
                  onDelete={(pid) => delPreguntaMut.mutate(pid)}
                  onMover={() => {}}
                />
              ))}
              {editable && (
                <Button onClick={() => openNewPregunta(null)}>+ Añadir pregunta</Button>
              )}
            </div>
          )}

          {/* Tarjetas de sección */}
          {secciones.map((s) => (
            <SeccionCard
              key={s.id}
              s={s}
              editable={editable}
              secciones={secciones}
              onEdit={() => openEditSeccion(s)}
              onDelete={() => handleDeleteSeccion(s)}
              onAddPregunta={openNewPregunta}
              onEditPregunta={openEditPregunta}
              onDeletePregunta={(pid) => delPreguntaMut.mutate(pid)}
              onMoverPregunta={(p, sid) => moverPreguntaMut.mutate({ preguntaId: p.id, seccionId: sid })}
              onUpdatePeso={(sId, peso) => updatePesoMut.mutate({ sId, peso })}
            />
          ))}

          {/* Zona de preguntas huérfanas */}
          {orphans.length > 0 && (
            <div className="rounded-xl border-2 border-rose-300 bg-rose-50 p-4 space-y-2">
              <p className="text-sm font-semibold text-rose-700">
                ⚠ {orphans.length} pregunta(s) sin sección — bloquearán la publicación
              </p>
              {orphans.map((p, idx) => (
                <PreguntaRow
                  key={p.id} p={p} idx={idx} secciones={secciones} editable={editable}
                  onEdit={openEditPregunta}
                  onDelete={(pid) => delPreguntaMut.mutate(pid)}
                  onMover={(preg, sid) => moverPreguntaMut.mutate({ preguntaId: preg.id, seccionId: sid })}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Niveles ── */}
      {tab === 'niveles' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <Button onClick={openNewNivel}>+ Añadir nivel</Button>
          </div>
          {niveles.length === 0 && (
            <p className="text-sm text-slate-400 italic">Sin niveles definidos. Al enviar, los profesores no recibirán observación.</p>
          )}
          {niveles.map((n) => {
            const bg = { green: 'bg-emerald-50 border-emerald-200', blue: 'bg-blue-50 border-blue-200', yellow: 'bg-amber-50 border-amber-200', red: 'bg-rose-50 border-rose-200', gray: 'bg-slate-50 border-slate-200' }
            return (
              <div key={n.id} className={`rounded-xl border p-4 flex items-start gap-4 ${bg[n.color] ?? bg.gray}`}>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-800">{n.nombre}</span>
                    <span className="text-xs text-slate-500">{n.porcentaje_min}% – {n.porcentaje_max}%</span>
                  </div>
                  <p className="text-sm text-slate-600 mt-1">{n.observacion}</p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" variant="secondary" onClick={() => openEditNivel(n)}>Editar</Button>
                  <Button size="sm" variant="danger" onClick={() => window.confirm('¿Eliminar?') && delNivelMut.mutate(n.id)}>×</Button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Tab: Estadísticas ── */}
      {tab === 'estadisticas' && (
        <div className="space-y-6">
          {!stats ? <p className="text-sm text-slate-400">Cargando estadísticas…</p> : (
            <>
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-xl bg-white border border-slate-200 p-4 text-center">
                  <p className="text-3xl font-bold text-indigo-600">{stats.total_respuestas_enviadas}</p>
                  <p className="text-xs text-slate-500 mt-1">Respuestas enviadas</p>
                </div>
                <div className="rounded-xl bg-white border border-slate-200 p-4 text-center">
                  <p className="text-3xl font-bold text-emerald-600">{stats.promedio_porcentaje != null ? `${stats.promedio_porcentaje}%` : '—'}</p>
                  <p className="text-xs text-slate-500 mt-1">Promedio general</p>
                </div>
                <div className="rounded-xl bg-white border border-slate-200 p-4 text-center">
                  <p className="text-3xl font-bold text-slate-700">{stats.distribucion_niveles?.length ?? 0}</p>
                  <p className="text-xs text-slate-500 mt-1">Niveles definidos</p>
                </div>
              </div>

              {stats.distribucion_niveles?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-3">Distribución por nivel</h3>
                  <div className="space-y-2">
                    {stats.distribucion_niveles.map((n) => (
                      <div key={n.nivel_id} className="flex items-center gap-3">
                        <span className="w-28 text-sm text-slate-600 truncate">{n.nombre}</span>
                        <div className="flex-1 bg-slate-100 rounded-full h-4 overflow-hidden">
                          <div className="h-full bg-indigo-400 rounded-full transition-all"
                            style={{ width: stats.total_respuestas_enviadas ? `${(n.count / stats.total_respuestas_enviadas) * 100}%` : '0%' }} />
                        </div>
                        <span className="w-8 text-right text-sm font-medium text-slate-700">{n.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Por pregunta</h3>
                <div className="space-y-4">
                  {stats.preguntas?.map((p, i) => (
                    <div key={p.pregunta_id} className="rounded-xl border border-slate-200 bg-white p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs rounded bg-slate-100 px-2 py-0.5 text-slate-600">{i + 1}</span>
                        <p className="text-sm font-medium text-slate-800">{p.texto}</p>
                        {p.promedio != null && <span className="ml-auto text-xs text-indigo-600 font-medium">Promedio: {p.promedio}</span>}
                      </div>
                      {p.opciones?.length > 0 && (
                        <div className="space-y-1">
                          {p.opciones.map((op) => (
                            <div key={op.opcion_id} className="flex items-center gap-2 text-xs">
                              <span className="w-32 text-slate-600 truncate">{op.texto}</span>
                              <div className="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden">
                                <div className="h-full bg-indigo-300 rounded-full"
                                  style={{ width: p.total_respuestas ? `${(op.conteo / p.total_respuestas) * 100}%` : '0%' }} />
                              </div>
                              <span className="w-8 text-right text-slate-500">{op.conteo}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Modal Pregunta ── */}
      {qModal && (
        <PreguntaModal
          key={editingQ?.id ?? 'nueva'}
          onClose={() => setQModal(false)}
          initial={editingQ}
          secciones={secciones}
          onSave={(q) => savePreguntaMut.mutate(q)}
          loading={savePreguntaMut.isPending}
        />
      )}

      {/* ── Modal Sección ── */}
      <Modal open={sModal} onClose={() => setSModal(false)} title={editingS ? 'Editar Sección' : 'Nueva Sección'}
        footer={<>
          <Button variant="secondary" onClick={() => setSModal(false)}>Cancelar</Button>
          <Button loading={saveSeccionMut.isPending}
            onClick={() => saveSeccionMut.mutate(editingS ? { id: editingS.id, ...sForm } : sForm)}>
            Guardar
          </Button>
        </>}>
        <div className="space-y-4">
          <FormField label="Título" required>
            <input value={sForm.titulo} onChange={(e) => setSForm((p) => ({ ...p, titulo: e.target.value }))} className={inputCls} placeholder="ej. Planeación docente" />
          </FormField>
          <FormField label="Descripción">
            <textarea value={sForm.descripcion ?? ''} onChange={(e) => setSForm((p) => ({ ...p, descripcion: e.target.value }))} rows={2} className={inputCls} placeholder="Descripción opcional" />
          </FormField>
          {!editingS && (
            <FormField label="Peso (%)" hint="Ajustable luego con el campo de la tarjeta de sección.">
              <input type="number" min={0} max={100} step={0.01} value={sForm.peso}
                onChange={(e) => setSForm((p) => ({ ...p, peso: e.target.value }))} className={inputCls + ' w-32'} />
            </FormField>
          )}
        </div>
      </Modal>

      {/* ── Modal Nivel ── */}
      <Modal open={nModal} onClose={() => setNModal(false)} title={editingN ? 'Editar Nivel' : 'Nuevo Nivel'}
        footer={<>
          <Button variant="secondary" onClick={() => setNModal(false)}>Cancelar</Button>
          <Button loading={saveNivelMut.isPending}
            onClick={() => saveNivelMut.mutate(editingN ? { id: editingN.id, ...nForm } : nForm)}>
            Guardar
          </Button>
        </>}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Nombre del nivel" required>
              <input value={nForm.nombre} onChange={(e) => setNForm((p) => ({ ...p, nombre: e.target.value }))} className={inputCls} placeholder="ej. Excelente" />
            </FormField>
            <FormField label="Color">
              <select value={nForm.color} onChange={(e) => setNForm((p) => ({ ...p, color: e.target.value }))} className={inputCls}>
                {NIVEL_COLORES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </FormField>
            <FormField label="% mínimo" required>
              <input type="number" min={0} max={100} step={0.01} value={nForm.porcentaje_min}
                onChange={(e) => setNForm((p) => ({ ...p, porcentaje_min: e.target.value }))} className={inputCls} placeholder="0.00" />
            </FormField>
            <FormField label="% máximo" required>
              <input type="number" min={0} max={100} step={0.01} value={nForm.porcentaje_max}
                onChange={(e) => setNForm((p) => ({ ...p, porcentaje_max: e.target.value }))} className={inputCls} placeholder="100.00" />
            </FormField>
          </div>
          <FormField label="Observación" required>
            <textarea value={nForm.observacion} onChange={(e) => setNForm((p) => ({ ...p, observacion: e.target.value }))} rows={3} className={inputCls} placeholder="Mensaje que verá el profesor al obtener este nivel." />
          </FormField>
        </div>
      </Modal>
    </div>
  )
}
