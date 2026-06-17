import client from './client'

export const getDashboard = (params) =>
  client.get('/reportes/dashboard/', { params })

export const getCumplimiento = (params) =>
  client.get('/reportes/cumplimiento/', { params })

export const getCumplimientoLicenciatura = (params) =>
  client.get('/reportes/cumplimiento-licenciatura/', { params })

export const getResumenAutoevaluacion = (params) =>
  client.get('/reportes/autoevaluacion/', { params })

export const getAutoevaluacionProfesores = (params) =>
  client.get('/reportes/autoevaluacion-profesores/', { params })
