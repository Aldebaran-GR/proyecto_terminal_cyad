/**
 * Tabla reutilizable.
 *
 * @param {Array}  columns — [{ key, label, render?, className? }]
 * @param {Array}  data    — array de objetos
 * @param {string} emptyText
 * @param {boolean} loading
 */
import Loading from './Loading'
import EmptyState from './EmptyState'

export default function Table({
  columns = [],
  data = [],
  emptyText = 'No hay registros',
  loading = false,
  rowKey = 'id',
}) {
  if (loading) return <Loading />

  if (!data.length) {
    return <EmptyState title={emptyText} />
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-3 text-left ${col.className ?? ''}`}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {data.map((row) => (
            <tr key={row[rowKey]} className="hover:bg-slate-50 transition-colors">
              {columns.map((col) => (
                <td key={col.key} className={`px-4 py-3 text-slate-700 ${col.className ?? ''}`}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
