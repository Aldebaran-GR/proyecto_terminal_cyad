import client from './client'

/* ─── Departamentos ───────────────────────────────────────── */
export const getDepartamentos = (params) => client.get('/departamentos/', { params })
export const createDepartamento = (data) => client.post('/departamentos/', data)
export const updateDepartamento = (id, data) => client.patch(`/departamentos/${id}/`, data)
export const deleteDepartamento = (id) => client.delete(`/departamentos/${id}/`)

/* ─── Licenciaturas ───────────────────────────────────────── */
export const getLicenciaturas = (params) => client.get('/licenciaturas/', { params })
export const createLicenciatura = (data) => client.post('/licenciaturas/', data)
export const updateLicenciatura = (id, data) => client.patch(`/licenciaturas/${id}/`, data)
export const deleteLicenciatura = (id) => client.delete(`/licenciaturas/${id}/`)

/* ─── UEA ─────────────────────────────────────────────────── */
export const getUEA = (params) => client.get('/uea/', { params })
export const createUEA = (data) => client.post('/uea/', data)
export const updateUEA = (id, data) => client.patch(`/uea/${id}/`, data)
export const deleteUEA = (id) => client.delete(`/uea/${id}/`)
export const importarUEA = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return client.post('/uea/import-csv/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/* ─── Periodos ────────────────────────────────────────────── */
export const getPeriodos = (params) => client.get('/periodos/', { params })
export const createPeriodo = (data) => client.post('/periodos/', data)
export const updatePeriodo = (id, data) => client.patch(`/periodos/${id}/`, data)
export const deletePeriodo = (id) => client.delete(`/periodos/${id}/`)
export const getPeriodoActivo = () => client.get('/periodos/', { params: { activo: true } })
