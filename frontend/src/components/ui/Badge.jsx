/**
 * Badge de estado para documentos y formularios.
 */
const presets = {
  BORRADOR: 'bg-slate-100 text-slate-600',
  PUBLICADO: 'bg-blue-100 text-blue-700',
  ENVIADO: 'bg-emerald-100 text-emerald-700',
  CERRADO: 'bg-slate-200 text-slate-500',
  ACTIVO: 'bg-emerald-100 text-emerald-700',
  INACTIVO: 'bg-slate-100 text-slate-500',
  ADMIN: 'bg-indigo-100 text-indigo-700',
  PROFESOR: 'bg-teal-100 text-teal-700',
}

export default function Badge({ label, variant }) {
  const cls = presets[variant] ?? presets[label] ?? 'bg-slate-100 text-slate-600'
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}
