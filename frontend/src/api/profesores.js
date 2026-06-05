import client from './client'

/* ─── Usuarios (solo para crear profesor) ─────────────────── */
export const createUsuario = (data) => client.post('/usuarios/', data)

/* ─── Profesores ──────────────────────────────────────────── */
export const getProfesores = (params) => client.get('/profesores/', { params })
export const getProfesor = (id) => client.get(`/profesores/${id}/`)
export const createProfesor = (data) => client.post('/profesores/', data)
export const updateProfesor = (id, data) => client.patch(`/profesores/${id}/`, data)
export const deleteProfesor = (id) => client.delete(`/profesores/${id}/`)
export const toggleActivoProfesor = (id) =>
  client.post(`/usuarios/${id}/toggle-activo/`)
