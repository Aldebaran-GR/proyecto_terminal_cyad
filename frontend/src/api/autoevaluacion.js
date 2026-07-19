import client from './client'

/* ─── Admin — Formularios ───────────────────────────────── */
export const getFormularios = (params) =>
  client.get('/formularios/', { params })

export const getFormulario = (id) =>
  client.get(`/formularios/${id}/`)

export const createFormulario = (data) =>
  client.post('/formularios/', data)

export const updateFormulario = (id, data) =>
  client.patch(`/formularios/${id}/`, data)

export const deleteFormulario = (id) =>
  client.delete(`/formularios/${id}/`)

export const publicarFormulario = (id) =>
  client.post(`/formularios/${id}/publicar/`)

export const cerrarFormulario = (id) =>
  client.post(`/formularios/${id}/cerrar/`)

// PUBLICADO o CERRADO → BORRADOR para reabrir edición.
export const despublicarFormulario = (id) =>
  client.post(`/formularios/${id}/despublicar/`)

// CERRADO → PUBLICADO (reactivar recepción de respuestas).
export const reabrirFormulario = (id) =>
  client.post(`/formularios/${id}/reabrir/`)

export const publicarRevisionFormulario = (id) =>
  client.post(`/formularios/${id}/publicar-revision/`)

// Clona el formulario (estructura completa, sin respuestas) en otro periodo.
export const duplicarFormulario = (id, data) =>
  client.post(`/formularios/${id}/duplicar/`, data)

export const getFormularioRespuestas = (id) =>
  client.get(`/formularios/${id}/respuestas/`)

export const getFormularioEstadisticas = (id) =>
  client.get(`/formularios/${id}/estadisticas/`)

/* ─── Admin — Preguntas ─────────────────────────────────── */
export const getPreguntas = (params) =>
  client.get('/preguntas/', { params })

export const createPregunta = (data) =>
  client.post('/preguntas/', data)

export const updatePregunta = (id, data) =>
  client.put(`/preguntas/${id}/`, data)

export const patchPregunta = (id, data) =>
  client.patch(`/preguntas/${id}/`, data)

export const deletePregunta = (id) =>
  client.delete(`/preguntas/${id}/`)

/* ─── Admin — Secciones ─────────────────────────────────── */
export const getSecciones = (params) =>
  client.get('/secciones/', { params })

export const createSeccion = (data) =>
  client.post('/secciones/', data)

export const updateSeccion = (id, data) =>
  client.patch(`/secciones/${id}/`, data)

export const deleteSeccion = (id) =>
  client.delete(`/secciones/${id}/`)

/* ─── Admin — Niveles de Desempeño ─────────────────────── */
export const getNivelesDesempeno = (params) =>
  client.get('/niveles-desempeno/', { params })

export const createNivelDesempeno = (data) =>
  client.post('/niveles-desempeno/', data)

export const updateNivelDesempeno = (id, data) =>
  client.patch(`/niveles-desempeno/${id}/`, data)

export const deleteNivelDesempeno = (id) =>
  client.delete(`/niveles-desempeno/${id}/`)

/* ─── Profesor — Formularios disponibles ───────────────── */
export const getFormulariosDisponibles = (params) =>
  client.get('/formularios-disponibles/', { params })

export const getFormularioDisponible = (id) =>
  client.get(`/formularios-disponibles/${id}/`)

/* ─── Profesor — Respuestas ─────────────────────────────── */
export const getRespuestas = (params) =>
  client.get('/respuestas/', { params })

export const getRespuesta = (id) =>
  client.get(`/respuestas/${id}/`)

export const createRespuesta = (data) =>
  client.post('/respuestas/', data)

export const updateRespuesta = (id, data) =>
  client.patch(`/respuestas/${id}/`, data)

export const enviarRespuesta = (id) =>
  client.post(`/respuestas/${id}/enviar/`)
