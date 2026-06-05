/**
 * Gestión de Profesores — Admin.
 * Crear: primero crea Usuario (email+password) y luego Profesor vinculado.
 * Editar: solo campos del perfil Profesor.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getProfesores, createProfesor, updateProfesor, createUsuario,
} from '../../../api/profesores'
import { getDepartamentos } from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Modal from '../../../components/ui/Modal'
import Table from '../../../components/ui/Table'
import Alert from '../../../components/ui/Alert'
import FormField, { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

const emptyCreate = () => ({
  email: '', nombre: '', password: '',
  nombre_completo: '', correo_institucional: '', numero_economico: '', departamento: '',
})
const emptyEdit = (row) => ({
  nombre_completo: row.nombre_completo,
  correo_institucional: row.correo_institucional,
  numero_economico: row.numero_economico ?? '',
  estado: row.estado,
})

export default function ProfesoresPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState(false)
  const [isEdit, setIsEdit] = useState(false)
  const [selected, setSelected] = useState(null)
  const [createForm, setCreateForm] = useState(emptyCreate())
  const [editForm, setEditForm] = useState({})
  const [apiError, setApiError] = useState(null)
  const [search, setSearch] = useState('')

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

  /* Crear: 1) POST /usuarios/, 2) POST /profesores/ */
  const createMut = useMutation({
    mutationFn: async (d) => {
      const userRes = await createUsuario({
        email: d.email, nombre: d.nombre, password: d.password, rol: 'PROFESOR',
      })
      return createProfesor({
        usuario_id: userRes.data.id,
        nombre_completo: d.nombre_completo,
        correo_institucional: d.correo_institucional,
        numero_economico: d.numero_economico || null,
        departamento: d.departamento || null,
      })
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['profesores'] }); closeModal() },
    onError: (e) => {
      const data = e.response?.data
      setApiError(data?.email?.[0] || data?.password?.[0] || data?.non_field_errors?.[0] || data?.detail || 'Error al crear el profesor.')
    },
  })

  const editMut = useMutation({
    mutationFn: (d) => updateProfesor(selected.id, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['profesores'] }); closeModal() },
    onError: (e) => setApiError(e.response?.data?.detail || 'Error al guardar.'),
  })

  const fc = (key) => (e) => setCreateForm((p) => ({ ...p, [key]: e.target.value }))
  const fe = (key) => (e) => setEditForm((p) => ({ ...p, [key]: e.target.value }))

  const columns = [
    {
      key: 'nombre_completo', label: 'Profesor',
      render: (v, row) => <div><p className="font-medium">{v}</p><p className="text-xs text-slate-400">{row.correo_institucional}</p></div>,
    },
    { key: 'numero_economico', label: 'N° Económico', className: 'w-28', render: (v) => v ?? <span className="text-slate-400">—</span> },
    {
      key: 'usuario', label: 'Email de acceso',
      render: (v) => <span className="text-xs text-slate-500">{v?.email}</span>,
    },
    {
      key: 'estado', label: 'Estado', className: 'w-24',
      render: (v) => <Badge label={v ? 'ACTIVO' : 'INACTIVO'} variant={v ? 'ACTIVO' : 'INACTIVO'} />,
    },
    {
      key: 'actions', label: '', className: 'w-24 text-right',
      render: (_, row) => (
        <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>Editar</Button>
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
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Cuenta de acceso</p>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Email institucional" required><input value={createForm.email} onChange={fc('email')} type="email" className={inputCls} placeholder="usuario@uam.mx" /></FormField>
            <FormField label="Nombre completo (display)" required><input value={createForm.nombre} onChange={fc('nombre')} className={inputCls} placeholder="Nombre para mostrar" /></FormField>
            <div className="col-span-2">
              <FormField label="Contraseña inicial" required><input value={createForm.password} onChange={fc('password')} type="password" className={inputCls} placeholder="Mínimo 8 caracteres" /></FormField>
            </div>
          </div>
          <hr className="border-slate-100" />
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Perfil del profesor</p>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Nombre completo" required><input value={createForm.nombre_completo} onChange={fc('nombre_completo')} className={inputCls} placeholder="Nombre oficial en documentos" /></FormField>
            <FormField label="Correo institucional"><input value={createForm.correo_institucional} onChange={fc('correo_institucional')} className={inputCls} placeholder="correo@cyad.uam.mx" /></FormField>
            <FormField label="Número económico"><input value={createForm.numero_economico} onChange={fc('numero_economico')} className={inputCls} placeholder="ej. 12345" /></FormField>
            <FormField label="Departamento">
              <select value={createForm.departamento} onChange={fc('departamento')} className={inputCls}>
                <option value="">-- Sin asignar --</option>
                {deptos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
              </select>
            </FormField>
          </div>
        </div>
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
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={editForm.estado ?? true} onChange={(e) => setEditForm((p) => ({ ...p, estado: e.target.checked }))} className="h-4 w-4 accent-indigo-600" />
            <span className="text-sm text-slate-700">Perfil activo</span>
          </label>
        </div>
      </Modal>
    </div>
  )
}
