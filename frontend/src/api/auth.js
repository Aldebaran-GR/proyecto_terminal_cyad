import client from './client'

export const login = (email, password) =>
  client.post('/auth/login/', { email, password })

export const refreshToken = (refresh) =>
  client.post('/auth/refresh/', { refresh })

export const me = () => client.get('/auth/me/')
