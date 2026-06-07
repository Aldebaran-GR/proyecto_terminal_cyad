/**
 * Vista pública de una Carta Temática (sin login, /publico/cartas/:id).
 *
 * El backend solo devuelve la carta si está en estado PUBLICADO; cualquier
 * otro caso es 404 → "Documento no disponible".
 */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getPublicCarta } from '../../api/documentos'
import PublicDocumentLayout from './PublicDocumentLayout'
import { CartaTematicaArticle } from './DocumentArticles'

export default function PublicCartaPage() {
  const { id } = useParams()
  const [carta, setCarta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true)
    getPublicCarta(id)
      .then((r) => { if (alive) setCarta(r.data) })
      .catch(() => { if (alive) setNotFound(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [id])

  if (loading) {
    return (
      <PublicDocumentLayout title="Cargando…">
        <p className="text-sm text-slate-400">Cargando documento…</p>
      </PublicDocumentLayout>
    )
  }

  if (notFound || !carta) {
    return (
      <PublicDocumentLayout title="Documento no disponible">
        <div className="rounded-xl bg-white border border-slate-200 p-8 text-center">
          <p className="text-base text-slate-700">
            Este documento no está disponible públicamente.
          </p>
          <p className="text-xs text-slate-500 mt-2">
            Puede haber sido eliminado, no estar publicado, o el enlace ser incorrecto.
          </p>
        </div>
      </PublicDocumentLayout>
    )
  }

  return (
    <PublicDocumentLayout title={carta.tipo_documento}>
      <CartaTematicaArticle carta={carta} />
    </PublicDocumentLayout>
  )
}
