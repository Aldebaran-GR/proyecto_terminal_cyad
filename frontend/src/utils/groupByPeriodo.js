/**
 * Agrupa filas por `periodo_clave` y devuelve arreglo ordenado con:
 *   [{ clave, fechaInicio, rows, isActivo }]
 *
 * Orden: periodo activo primero (si aparece); resto por `periodo_fecha_inicio`
 * descendente (más reciente primero). Filas sin periodo caen a "Sin periodo"
 * al final.
 */
export function groupByPeriodo(rows, activoClave = null) {
  const groups = new Map()
  for (const row of rows) {
    const clave = row.periodo_clave || 'Sin periodo'
    if (!groups.has(clave)) {
      groups.set(clave, {
        clave,
        fechaInicio: row.periodo_fecha_inicio || null,
        rows: [],
        isActivo: clave === activoClave,
      })
    }
    groups.get(clave).rows.push(row)
  }
  return Array.from(groups.values()).sort((a, b) => {
    if (a.isActivo && !b.isActivo) return -1
    if (!a.isActivo && b.isActivo) return 1
    // Más reciente primero (fechaInicio desc). Nulls al final.
    if (!a.fechaInicio && !b.fechaInicio) return a.clave.localeCompare(b.clave)
    if (!a.fechaInicio) return 1
    if (!b.fechaInicio) return -1
    return b.fechaInicio.localeCompare(a.fechaInicio)
  })
}
