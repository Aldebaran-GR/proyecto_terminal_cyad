/**
 * Wrapper de campo de formulario: label + input/select/textarea + mensaje de error.
 *
 * Uso:
 *   <FormField label="Correo" error={errors.email?.message}>
 *     <input {...register('email')} type="email" />
 *   </FormField>
 */
import { Children, cloneElement, isValidElement, useId } from 'react'

export default function FormField({ label, error, required = false, children, hint }) {
  const generatedId = useId()

  // Asocia el <label> con el campo: si hay un único hijo (input/select/textarea)
  // sin id propio, le inyectamos uno y lo enlazamos vía htmlFor (accesibilidad).
  let fieldId
  let renderedChildren = children
  const childArray = Children.toArray(children)
  if (label && childArray.length === 1 && isValidElement(childArray[0])) {
    fieldId = childArray[0].props.id ?? generatedId
    if (!childArray[0].props.id) {
      renderedChildren = cloneElement(childArray[0], { id: fieldId })
    }
  }

  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={fieldId} className="block text-sm font-medium text-slate-700">
          {label}
          {required && <span className="ml-1 text-rose-500">*</span>}
        </label>
      )}
      {/* Inyecta clases de error al primer child via wrapper div */}
      <div className={error ? '[&_input]:border-rose-400 [&_select]:border-rose-400 [&_textarea]:border-rose-400' : ''}>
        {renderedChildren}
      </div>
      {hint && !error && (
        <p className="text-xs text-slate-500">{hint}</p>
      )}
      {error && (
        <p className="text-xs text-rose-600" role="alert">{error}</p>
      )}
    </div>
  )
}

/* Clases base compartidas para inputs del proyecto */
export const inputCls =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 ' +
  'placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 ' +
  'focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500'
