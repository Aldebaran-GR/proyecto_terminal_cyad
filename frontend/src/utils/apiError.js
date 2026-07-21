/**
 * El backend envuelve todos los errores DRF en {success, status_code, errors}
 * (ver backend/core/exceptions.py). `errors` es el detalle original de DRF:
 *   - dict con campos conocidos (detail, non_field_errors, preguntas_faltantes)
 *     o campos de un serializer (clave, nombre, estado, ...) → listas de strings.
 *   - lista de strings, cuando se levanta ValidationError con un string plano.
 *
 * Muchas páginas leían `e.response.data.detail` directamente, saltando el
 * wrapper, y por eso solo mostraban el mensaje de fallback genérico aunque el
 * backend hubiera devuelto un error específico.
 */
export function parseApiError(data, fallback = 'Ocurrió un error.') {
  const errors = data?.errors ?? data

  if (Array.isArray(errors)) {
    return typeof errors[0] === 'string' ? errors[0] : fallback
  }

  if (errors && typeof errors === 'object') {
    if (errors.preguntas_faltantes) {
      return { preguntasFaltantes: errors.preguntas_faltantes }
    }
    if (typeof errors.detail === 'string') return errors.detail
    if (Array.isArray(errors.non_field_errors) && errors.non_field_errors[0]) {
      return errors.non_field_errors[0]
    }
    // Cualquier otro campo del serializer (clave, nombre, estado, enlace, ...)
    // — toma el primer mensaje de la primera lista no vacía.
    for (const key of Object.keys(errors)) {
      const val = errors[key]
      if (Array.isArray(val) && typeof val[0] === 'string') return val[0]
    }
  }

  return data?.detail || fallback
}
