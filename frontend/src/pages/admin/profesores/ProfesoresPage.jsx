/**
 * Gestión de Profesores — Admin.
 * Crear: primero crea Usuario (email+password) y luego Profesor vinculado.
 * Editar: solo campos del perfil Profesor.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getProfesores, updateProfesor, createProfesorAtomico,
  setUsuarioPassword, deleteProfesor,
} from '../../../api/profesores'
import { getDepartamentos } from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Modal from '../../../components/ui/Modal'
import Table from '../../../components/ui/Table'
import Alert from '../../../components/ui/Alert'
import FormField, { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

// El `nombre` del Usuario y el `nombre_completo` del Profesor son siempre
// el mismo texto; lo mismo aplica al `email` (login) y `correo_institucional`
// (perfil). La UI captura un único valor para cada par y al guardar se
// replica al otro campo del backend.
const emptyCreate = () => ({
  email: '', password: '',
  nombre_completo: '', numero_economico: '', departamento: '',
})
const emptyEdit = (row) => ({
  nombre_completo: row.nombre_completo,
  correo_institucional: row.correo_institucional,
  numero_economico: row.numero_economico ?? '',
  departamento: row.departamento ?? '',
  estado: row.estado,
})

/**
 * Lee un error de DRF tomando en cuenta el wrapper del backend
 * ({success, status_code, errors: {...}}) y devuelve un mensaje legible.
 * Prioriza campos específicos sobre detalles genéricos.
 */
function extractError(e, fallback = 'Error.') {
  if (e?.message && !e.response) return e.message  // error de red o de cliente
  const data = e?.response?.data ?? {}
  // El wrapper coloca los errores dentro de `errors`; si por algún motivo
  // viniera directo, también lo aceptamos.
  const errs = data.errors ?? data
  if (typeof errs === 'string') return errs

  // Convertir { campo: [msg, ...], ... } al primer mensaje campo-prefijado
  const claves = ['email', 'password', 'nombre', 'nombre_completo',
                  'correo_institucional', 'numero_economico', 'departamento',
                  'usuario_id', 'non_field_errors']
  for (const k of claves) {
    const v = errs?.[k]
    if (Array.isArray(v) && v[0]) {
      return k === 'non_field_errors' ? v[0] : `${k}: ${v[0]}`
    }
    if (typeof v === 'string') return v
  }
  return data.detail || errs?.detail || fallback
}

export default function ProfesoresPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState(false)
  const [isEdit, setIsEdit] = useState(false)
  const [selected, setSelected] = useState(null)
  const [createForm, setCreateForm] = useState(emptyCreate())
  const [editForm, setEditForm] = useState({})
  const [apiError, setApiError] = useState(null)
  const [search, setSearch] = useState('')

  // Modal independiente para restablecer contraseña de un profesor existente.
  const [pwdTarget, setPwdTarget] = useState(null)   // perfil del profesor
  const [pwdValue, setPwdValue] = useState('')
  const [pwdSaved, setPwdSaved] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['profesores', search],
    queryFn: () => getProfesores(search ? { search } : undefined).then((r) => r.data?.results ?? r.data ?? []),
  })
  const { data: deptos = [] } = useQuery({
    queryKey: ['departamentos'],
    queryFn: () => getDepartamentos().then((r) => r.data?.results ?? r.data ?? []),
  })

  const openCreate = () => { setIsEdit(false); setCreateForm(emptyCreate()); setApiError(null); setModal(true) }
  const openEdit = (row) => { setIsEdit(true); setSelected(row); setEditForm(emptyEdit(row)); setApiError(null); setModal(true) }
  const closeModal = () => { setModal(false); setApiError(null) }

  /* Crear: una sola llamada atómica que el backend gestiona dentro de
     `transaction.atomic()`. Si algo falla, no quedan registros huérfanos
     (causa común del bug "ya existe un usuario con este correo" después
     de un intento previo fallido). */
  const createMut = useMutation({
    mutationFn: (d) => createProfesorAtomico({
      email: d.email,
      password: d.password,
      nombre_completo: d.nombre_completo,
      numero_economico: d.numero_economico || null,
      departamento: d.departamento || null,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['profesores'] }); closeModal() },
    onError: (e) => setApiError(extractError(e, 'Error al crear el profesor.')),
  })

  const editMut = useMutation({
    mutationFn: (d) => updateProfesor(selected.id, { ...d, departamento: d.departamento || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['profesores'] }); closeModal() },
    onError: (e) => setApiError(extractError(e, 'Error al guardar.')),
  })

  // Eliminar profesor — borra el perfil y su cuenta de Usuario. Los
  // documentos (cartas / requisitos) se conservan con un snapshot del
  // nombre y correo para que el historial siga siendo legible.
  const deleteMut = useMutation({
    mutationFn: (row) => deleteProfesor(row.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profesores'] }),
    onError: (e) => setApiError(extractError(e, 'No se pudo eliminar el profesor.')),
  })

  const onDeleteClick = (row) => {
    if (window.confirm(
      `¿Eliminar al profesor "${row.nombre_completo}" y su cuenta de acceso?\n\n` +
      'Sus Cartas Temáticas y Requisitos de Recuperación se conservarán ' +
      'con su nombre como histórico. Esta acción no se puede deshacer.'
    )) {
      deleteMut.mutate(row)
    }
  }

  // Restablecer contraseña — actúa sobre el Usuario (Profesor.usuario.id).
  const pwdMut = useMutation({
    mutationFn: ({ usuarioId, password }) => setUsuarioPassword(usuarioId, password),
    onSuccess: () => {
      setPwdSaved(true)
      // Auto-cierre del aviso tras 2 segundos
      setTimeout(() => {
        setPwdTarget(null)
        setPwdValue('')
        setPwdSaved(false)
      }, 1800)
    },
    onError: (e) => setApiError(extractError(e, 'No se pudo restablecer la contraseña.')),
  })

  const openPwdReset = (row) => {
    setApiError(null)
    setPwdTarget(row)
    setPwdValue('')
    setPwdSaved(false)
  }
  const closePwdReset = () => {
    setPwdTarget(null)
    setPwdValue('')
    setPwdSaved(false)
    setApiError(null)
  }

  const fc = (key) => (e) => setCreateForm((p) => ({ ...p, [key]: e.target.value }))
  const fe = (key) => (e) => setEditForm((p) => ({ ...p, [key]: e.target.value }))

  const columns = [
    {
      key: 'nombre_completo', label: 'Profesor',
      render: (v, row) => <div><p className="font-medium">{v}</p><p className="text-xs text-slate-400">{row.correo_institucional}</p></div>,
    },
    { key: 'numero_economico', label: 'N° Económico', className: 'w-28', render: (v) => v ?? <span className="text-slate-400">—</span> },
    { key: 'departamento_nombre', label: 'Departamento', className: 'w-40', render: (v) => v ?? <span className="text-slate-400">—</span> },
    {
      key: 'usuario', label: 'Email de acceso',
      render: (v) => <span className="text-xs text-slate-500">{v?.email}</span>,
    },
    {
      key: 'estado', label: 'Estado', className: 'w-24',
      render: (v) => <Badge label={v ? 'ACTIVO' : 'INACTIVO'} variant={v ? 'ACTIVO' : 'INACTIVO'} />,
    },
    {
      key: 'actions', label: '', className: 'w-72 text-right',
      render: (_, row) => (
        <div className="flex justify-end gap-2 flex-wrap">
          <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>Editar</Button>
          <Button size="sm" variant="secondary" onClick={() => openPwdReset(row)}>Contraseña</Button>
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
        <h1 className="text-xl font-bold text-slate-900">Profesores</h1>
        <Button onClick={openCreate}>+ Nuevo Profesor</Button>
      </div>
      {apiError && !modal && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}

      <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar por nombre, correo o N° económico…" className={inputCls + ' max-w-sm'} />

      <Table columns={columns} data={data ?? []} loading={isLoading} emptyText="Sin profesores registrados" />

      {/* Modal Crear */}
      <Modal open={modal && !isEdit} onClose={closeModal} title="Nuevo Profesor" size="lg"
        footer={<>
          <Button variant="secondary" onClick={closeModal}>Cancelar</Button>
          <Button loading={createMut.isPending} onClick={() => createMut.mutate(createForm)}>Crear Profesor</Button>
        </>}>
        {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}
        <div className="space-y-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Datos del profesor</p>
          <FormField
            label="Nombre completo"
            required
            hint="Se usa en el saludo de la app y en los documentos públicos firmados."
          >
            <input
              value={createForm.nombre_completo}
              onChange={fc('nombre_completo')}
              className={inputCls}
              placeholder="ej. Mariana López Hernández"
            />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Número económico">
              <input value={createForm.numero_economico} onChange={fc('numero_economico')} className={inputCls} placeholder="ej. 12345" />
            </FormField>
            <FormField label="Departamento">
              <select value={createForm.departamento} onChange={fc('departamento')} className={inputCls}>
                <option value="">-- Sin asignar --</option>
                {deptos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
              </select>
            </FormField>
          </div>

          <hr className="border-slate-100" />
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Cuenta de acceso</p>
          <div className="grid grid-cols-2 gap-4">
            <FormField
              label="Correo institucional"
              required
              hint="Se usa también para iniciar sesión."
            >
              <input value={createForm.email} onChange={fc('email')} type="email" className={inputCls} placeholder="usuario@uam.mx" />
            </FormField>
            <FormField
              label="Contraseña inicial"
              required
              hint="Visible para que verifiques la captura."
            >
              <input value={createForm.password} onChange={fc('password')} type="text" className={inputCls} placeholder="Mínimo 8 caracteres" autoComplete="new-password" />
            </FormField>
          </div>
        </div>
      </Modal>

      {/* Modal Restablecer contraseña */}
      <Modal
        open={!!pwdTarget}
        onClose={closePwdReset}
        title={`Restablecer contraseña — ${pwdTarget?.nombre_completo ?? ''}`}
        footer={pwdSaved ? null : (
          <>
            <Button variant="secondary" onClick={closePwdReset}>Cancelar</Button>
            <Button
              loading={pwdMut.isPending}
              disabled={!pwdValue.trim()}
              onClick={() => pwdMut.mutate({
                usuarioId: pwdTarget.usuario?.id,
                password: pwdValue,
              })}
            >
              Guardar nueva contraseña
            </Button>
          </>
        )}
      >
        {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}
        {pwdSaved ? (
          <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-800">
            ✓ Contraseña actualizada. El profesor podrá ingresar con la nueva
            contraseña a partir de su próximo inicio de sesión.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="text-xs text-slate-500">
              Cuenta de acceso:&nbsp;
              <span className="font-mono">{pwdTarget?.usuario?.email}</span>
            </div>
            <FormField
              label="Nueva contraseña"
              required
              hint="Visible para que verifiques la captura. El profesor la usará al iniciar sesión."
            >
              <input
                value={pwdValue}
                onChange={(e) => setPwdValue(e.target.value)}
                type="text"
                className={inputCls}
                placeholder="Mínimo 8 caracteres"
                autoComplete="new-password"
              />
            </FormField>
          </div>
        )}
      </Modal>

      {/* Modal Editar */}
      <Modal open={modal && isEdit} onClose={closeModal} title="Editar Perfil del Profesor"
        footer={<>
          <Button variant="secondary" onClick={closeModal}>Cancelar</Button>
          <Button loading={editMut.isPending} onClick={() => editMut.mutate(editForm)}>Guardar</Button>
        </>}>
        {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}
        <div className="space-y-4">
          <FormField label="Nombre completo"><input value={editForm.nombre_completo ?? ''} onChange={fe('nombre_completo')} className={inputCls} /></FormField>
          <FormField label="Correo institucional"><input value={editForm.correo_institucional ?? ''} onChange={fe('correo_institucional')} className={inputCls} /></FormField>
          <FormField label="Número económico"><input value={editForm.numero_economico ?? ''} onChange={fe('numero_economico')} className={inputCls} /></FormField>
          <FormField label="Departamento">
            <select value={editForm.departamento ?? ''} onChange={fe('departamento')} className={inputCls}>
              <option value="">-- Sin asignar --</option>
              {deptos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
            </select>
          </FormField>
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={editForm.estado ?? true}
              onChange={(e) => setEditForm((p) => ({ ...p, estado: e.target.checked }))}
              className="mt-0.5 h-4 w-4 accent-indigo-600"
            />
            <span className="text-sm text-slate-700">
              Cuenta activa (puede iniciar sesión)
              <span className="block text-xs text-slate-400 mt-0.5">
                Al desmarcarlo, el profesor dejará de poder ingresar al sistema.
                Sus documentos se conservan tal cual.
              </span>
            </span>
          </label>
        </div>
      </Modal>
    </div>
  )
}
