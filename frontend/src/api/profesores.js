import client from './client'

/* ─── Usuarios (solo para crear profesor) ─────────────────── */
export const createUsuario = (data) => client.post('/usuarios/', data)

/* ─── Profesores ──────────────────────────────────────────── */
export const getProfesores = (params) => client.get('/profesores/', { params })
export const getProfesor = (id) => client.get(`/profesores/${id}/`)
export const createProfesor = (data) => client.post('/profesores/', data)
export const updateProfesor = (id, data) => client.patch(`/profesores/${id}/`, data)
export const deleteProfesor = (id) => client.delete(`/profesores/${id}/`)

// Crea Usuario + Profesor en una sola llamada atómica (no deja huérfanos
// si falla en el camino). Reutiliza un Usuario huérfano si existe.
export const createProfesorAtomico = (data) =>
  client.post('/profesores/crear-con-usuario/', data)
export const toggleActivoProfesor = (id) =>
  client.post(`/usuarios/${id}/toggle-activo/`)

// Restablecer contraseña del usuario (admin).
// Recibe el id del Usuario (no el del Profesor).
export const setUsuarioPassword = (usuarioId, password) =>
  client.post(`/usuarios/${usuarioId}/set-password/`, { password })
