import client from './client'

/* ─── Cartas Temáticas ───────────────────────────────────── */
export const getCartas = (params) =>
  client.get('/cartas-tematicas/', { params })

export const getCarta = (id) =>
  client.get(`/cartas-tematicas/${id}/`)

export const createCarta = (data) =>
  client.post('/cartas-tematicas/', data)

export const updateCarta = (id, data) =>
  client.put(`/cartas-tematicas/${id}/`, data)

export const deleteCarta = (id) =>
  client.delete(`/cartas-tematicas/${id}/`)

export const cambiarEstadoCarta = (id, estado) =>
  client.post(`/cartas-tematicas/${id}/cambiar-estado/`, { estado })

/* ─── Requisitos de Recuperación ────────────────────────── */
export const getRequisitos = (params) =>
  client.get('/requisitos-recuperacion/', { params })

export const getRequisito = (id) =>
  client.get(`/requisitos-recuperacion/${id}/`)

export const createRequisito = (data) =>
  client.post('/requisitos-recuperacion/', data)

export const updateRequisito = (id, data) =>
  client.put(`/requisitos-recuperacion/${id}/`, data)

export const deleteRequisito = (id) =>
  client.delete(`/requisitos-recuperacion/${id}/`)

export const cambiarEstadoRequisito = (id, estado) =>
  client.post(`/requisitos-recuperacion/${id}/cambiar-estado/`, { estado })
