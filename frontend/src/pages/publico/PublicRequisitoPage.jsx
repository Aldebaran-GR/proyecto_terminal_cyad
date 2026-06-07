/**
 * Vista pública de un Requisito de Recuperación (sin login,
 * /publico/requisitos/:id). Solo aparece si está PUBLICADO.
 */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getPublicRequisito } from '../../api/documentos'
import PublicDocumentLayout from './PublicDocumentLayout'
import { RequisitoArticle } from './DocumentArticles'

export default function PublicRequisitoPage() {
  const { id } = useParams()
  const [doc, setDoc] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true)
    getPublicRequisito(id)
      .then((r) => { if (alive) setDoc(r.data) })
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

  if (notFound || !doc) {
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
    <PublicDocumentLayout title={doc.tipo_documento}>
      <RequisitoArticle doc={doc} />
    </PublicDocumentLayout>
  )
}
