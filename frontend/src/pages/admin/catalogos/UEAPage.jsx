/**
 * Catálogo de UEA — Admin. Incluye importación CSV.
 */
import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getUEA, createUEA, updateUEA, deleteUEA, importarUEA, getLicenciaturas, getAreas,
} from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Modal from '../../../components/ui/Modal'
import Table from '../../../components/ui/Table'
import Alert from '../../../components/ui/Alert'
import FormField, { inputCls } from '../../../components/ui/FormField'
import Badge from '../../../components/ui/Badge'

const TIPOS = [{ value: 'OBLIGATORIA', label: 'Obligatoria' }, { value: 'OPTATIVA', label: 'Optativa' }]

const empty = () => ({
  clave: '', nombre: '', licenciatura: '', area: '', trimestre: '',
  tipo: 'OBLIGATORIA', creditos: '', liga: '', estado: true,
})

export default function UEAPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState(false)
  const [csvModal, setCsvModal] = useState(false)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(empty())
  const [apiError, setApiError] = useState(null)
  const [csvResult, setCsvResult] = useState(null)
  const fileRef = useRef()
  const [search, setSearch] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['uea', search],
    queryFn: () => getUEA(search ? { search } : undefined).then((r) => r.data?.results ?? r.data ?? []),
  })
  const { data: lics = [] } = useQuery({
    queryKey: ['licenciaturas'],
    queryFn: () => getLicenciaturas().then((r) => r.data?.results ?? r.data ?? []),
  })
  const { data: areas = [] } = useQuery({
    queryKey: ['areas'],
    queryFn: () => getAreas().then((r) => r.data?.results ?? r.data ?? []),
  })

  const openCreate = () => { setSelected(null); setForm(empty()); setModal(true) }
  const openEdit = (row) => {
    setSelected(row)
    setForm({
      clave: row.clave, nombre: row.nombre,
      licenciatura: row.licenciatura ?? '',
      area: row.area ?? '',
      trimestre: row.trimestre ?? '',
      tipo: row.tipo, creditos: row.creditos ?? '',
      liga: row.liga ?? '', estado: row.estado,
    })
    setModal(true)
  }
  const closeModal = () => { setModal(false); setApiError(null) }

  const saveMut = useMutation({
    mutationFn: (d) => {
      const payload = {
        ...d,
        licenciatura: d.licenciatura || null,
        area: d.area || null,
        trimestre: d.trimestre || '',
        creditos: d.creditos !== '' ? Number(d.creditos) : null,
      }
      return selected ? updateUEA(selected.id, payload) : createUEA(payload)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['uea'] }); closeModal() },
    onError: (e) => setApiError(e.response?.data?.clave?.[0] || e.response?.data?.detail || 'Error al guardar.'),
  })
  const delMut = useMutation({
    mutationFn: (id) => deleteUEA(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['uea'] }),
    onError: () => setApiError('No se puede eliminar esta UEA (tiene documentos asociados).'),
  })
  const csvMut = useMutation({
    mutationFn: (file) => importarUEA(file),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['uea'] })
      setCsvResult(r.data)
    },
    onError: (e) => setApiError(e.response?.data?.detail || 'Error en la importación CSV.'),
  })

  const f = (key) => (e) => setForm((p) => ({ ...p, [key]: e.target.value }))

  const columns = [
    { key: 'clave', label: 'Clave', className: 'w-28 font-mono text-xs' },
    { key: 'nombre', label: 'UEA' },
    { key: 'licenciatura_nombre', label: 'Licenciatura', render: (v) => v ?? <span className="text-slate-400">—</span> },
    { key: 'area_nombre', label: 'Área', render: (v) => v ?? <span className="text-slate-400">—</span> },
    { key: 'tipo', label: 'Tipo', className: 'w-24', render: (v) => <span className="text-xs">{v}</span> },
    { key: 'estado', label: 'Estado', className: 'w-24', render: (v) => <Badge label={v ? 'ACTIVO' : 'INACTIVO'} variant={v ? 'ACTIVO' : 'INACTIVO'} /> },
    {
      key: 'actions', label: '', className: 'w-32 text-right',
      render: (_, row) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(row)}>Editar</Button>
          <Button size="sm" variant="danger" onClick={() => window.confirm('¿Eliminar?') && delMut.mutate(row.id)}>Eliminar</Button>
        </div>
      ),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-900">UEA</h1>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => { setCsvResult(null); setCsvModal(true) }}>Importar CSV</Button>
          <Button onClick={openCreate}>+ Nueva UEA</Button>
        </div>
      </div>
      {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}

      {/* Buscador */}
      <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar por clave o nombre…" className={inputCls + ' max-w-sm'} />

      <Table columns={columns} data={data ?? []} loading={isLoading} emptyText="Sin UEA registradas" />

      {/* Modal crear/editar */}
      <Modal open={modal} onClose={closeModal} title={selected ? 'Editar UEA' : 'Nueva UEA'} size="lg"
        footer={<>
          <Button variant="secondary" onClick={closeModal}>Cancelar</Button>
          <Button loading={saveMut.isPending} onClick={() => saveMut.mutate(form)}>Guardar</Button>
        </>}>
        {apiError && <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>}
        <div className="grid grid-cols-2 gap-4">
          <FormField label="Clave" required><input value={form.clave} onChange={f('clave')} className={inputCls} placeholder="1403004" /></FormField>
          <FormField label="Tipo">
            <select value={form.tipo} onChange={f('tipo')} className={inputCls}>
              {TIPOS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </FormField>
          <div className="col-span-2">
            <FormField label="Nombre" required><input value={form.nombre} onChange={f('nombre')} className={inputCls} placeholder="Nombre de la UEA" /></FormField>
          </div>
          <FormField label="Licenciatura">
            <select value={form.licenciatura} onChange={f('licenciatura')} className={inputCls}>
              <option value="">-- Ninguna --</option>
              {lics.map((l) => <option key={l.id} value={l.id}>{l.nombre}</option>)}
            </select>
          </FormField>
          <FormField label="Trimestre" hint="Acepta entero (1–12) o rango romano (ej. VII-XII)">
            <input type="text" value={form.trimestre} onChange={f('trimestre')} className={inputCls} placeholder="6 o VII-XII" />
          </FormField>
          <FormField label="Área">
            <select value={form.area} onChange={f('area')} className={inputCls}>
              <option value="">-- Ninguna --</option>
              {areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.descripcion ? `${a.nombre} — ${a.descripcion}` : a.nombre}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Créditos">
            <input type="number" min={0} value={form.creditos} onChange={f('creditos')} className={inputCls} placeholder="ej. 8" />
          </FormField>
          <div className="col-span-2">
            <FormField label="Liga (página oficial de la UEA)" hint="Opcional — se muestra en la vista pública de la Carta Temática">
              <input type="url" value={form.liga} onChange={f('liga')} className={inputCls} placeholder="https://cyad.azc.uam.mx/..." />
            </FormField>
          </div>
          <label className="col-span-2 flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.estado} onChange={(e) => setForm((p) => ({ ...p, estado: e.target.checked }))} className="h-4 w-4 accent-indigo-600" />
            <span className="text-sm text-slate-700">Activo</span>
          </label>
        </div>
      </Modal>

      {/* Modal importación CSV */}
      <Modal open={csvModal} onClose={() => { setCsvModal(false); setCsvResult(null) }} title="Importar UEA desde CSV"
        footer={!csvResult && (
          <>
            <Button variant="secondary" onClick={() => setCsvModal(false)}>Cancelar</Button>
            <Button loading={csvMut.isPending} onClick={() => fileRef.current.click()}>Seleccionar archivo</Button>
            <input ref={fileRef} type="file" accept=".csv" className="hidden"
              onChange={(e) => { if (e.target.files[0]) csvMut.mutate(e.target.files[0]) }} />
          </>
        )}>
        {csvResult ? (
          <div className="space-y-2 text-sm">
            <p className="text-emerald-600 font-medium">✓ Importación completada</p>
            <p>Creadas: <strong>{csvResult.created ?? 0}</strong></p>
            <p>Actualizadas: <strong>{csvResult.updated ?? 0}</strong></p>
            <p>Errores: <strong>{csvResult.errors?.length ?? 0}</strong></p>
            {csvResult.errors?.length > 0 && (
              <ul className="text-rose-600 text-xs mt-2">{csvResult.errors.map((e, i) => <li key={i}>{typeof e === 'string' ? e : JSON.stringify(e)}</li>)}</ul>
            )}
            <Button className="mt-2" onClick={() => { setCsvModal(false); setCsvResult(null) }}>Cerrar</Button>
          </div>
        ) : (
          <div className="text-sm text-slate-600 space-y-2">
            <p>El CSV debe tener las columnas:</p>
            <code className="block rounded bg-slate-50 p-3 text-xs">
              clave, nombre, licenciatura_clave, trimestre, tipo, creditos, area_nombre, area_descripcion, url
            </code>
            <p className="text-xs text-slate-400">area_nombre, area_descripcion y url son opcionales. trimestre acepta entero o rango romano.</p>
            <p className="text-slate-400">Rows existentes (por clave) se actualizan; nuevas se crean.</p>
          </div>
        )}
      </Modal>
    </div>
  )
}
