/**
 * Cliente HTTP para los endpoints públicos (sin JWT).
 *
 * La home pública y las páginas /publico/* consumen estos endpoints. Como
 * son AllowAny en backend, no enviamos Authorization: el cliente axios
 * está aislado del cliente con JWT (`api/client.js`).
 */
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export const publicClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

/* ─── Catálogos públicos ─────────────────────────────────────────────── */
export const getPublicLicenciaturas = () =>
  publicClient.get('/publico/licenciaturas/')

export const getPublicUEA = (params) =>
  publicClient.get('/publico/uea/', { params })

/* ─── Documentos públicos ────────────────────────────────────────────── */
// Listas — soportan ?licenciatura= y ?uea=
export const getPublicCartas = (params) =>
  publicClient.get('/publico/cartas/', { params })

export const getPublicRequisitos = (params) =>
  publicClient.get('/publico/requisitos/', { params })

// Detalle por id (ya existían como funciones separadas en api/documentos.js,
// pero al usar el cliente público quedan aisladas del JWT)
export const getPublicCarta = (id) =>
  publicClient.get(`/publico/cartas/${id}/`)

export const getPublicRequisito = (id) =>
  publicClient.get(`/publico/requisitos/${id}/`)
