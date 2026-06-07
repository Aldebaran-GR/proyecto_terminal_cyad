/**
 * Vista previa de un Requisito de Recuperación — mismo formato que la
 * vista pública, con barra superior de acciones (Editar / Eliminar).
 * Si está PUBLICADO se incluye también "Ver pública ↗".
 *
 * Editar y Eliminar despublican automáticamente si el documento estaba
 * publicado.
 */
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getRequisito, deleteRequisito, cambiarEstadoRequisito } from '../../../api/documentos'
import Button from '../../../components/ui/Button'
import Alert from '../../../components/ui/Alert'
import Badge from '../../../components/ui/Badge'
import Loading from '../../../components/ui/Loading'
import PublicDocumentLayout from '../../publico/PublicDocumentLayout'
import { RequisitoArticle } from '../../publico/DocumentArticles'

export default function RequisitoPreviewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [apiError, setApiError] = useState(null)

  const { data: doc, isLoading } = useQuery({
    queryKey: ['requisito', id],
    queryFn: () => getRequisito(id).then((r) => r.data),
  })

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['requisito', id] })
    qc.invalidateQueries({ queryKey: ['requisitos'] })
    qc.invalidateQueries({ queryKey: ['requisitos', 'dashboard'] })
  }
  const onError = (e) =>
    setApiError(
      e.response?.data?.detail
      || e.response?.data?.errors?.estado
      || 'Error.'
    )

  const editMut = useMutation({
    mutationFn: async () => {
      if (doc?.estado === 'PUBLICADO') {
        await cambiarEstadoRequisito(id, 'BORRADOR')
      }
    },
    onSuccess: () => {
      invalidate()
      navigate(`/profesor/requisitos/${id}`)
    },
    onError,
  })

  const deleteMut = useMutation({
    mutationFn: async () => {
      if (doc?.estado === 'PUBLICADO') {
        await cambiarEstadoRequisito(id, 'BORRADOR')
      }
      return deleteRequisito(id)
    },
    onSuccess: () => {
      invalidate()
      navigate('/profesor/requisitos')
    },
    onError,
  })

  const onEditClick = () => {
    if (doc?.estado === 'PUBLICADO') {
      if (!window.confirm(
        'Este requisito está PUBLICADO. Para editarlo se despublicará primero. ¿Continuar?'
      )) return
    }
    editMut.mutate()
  }
  const onDeleteClick = () => {
    const aviso = doc?.estado === 'PUBLICADO'
      ? 'Este requisito está PUBLICADO. Se despublicará y eliminará. ¿Continuar?'
      : '¿Eliminar este requisito? Esta acción no se puede deshacer.'
    if (window.confirm(aviso)) deleteMut.mutate()
  }

  if (isLoading) return <Loading text="Cargando vista previa..." />
  if (!doc) {
    return (
      <div className="p-8">
        <p className="text-sm text-slate-500">No se pudo cargar el documento.</p>
        <Link to="/profesor/requisitos" className="text-indigo-600 text-sm hover:underline">
          ← Volver
        </Link>
      </div>
    )
  }

  const isPublicado = doc.estado === 'PUBLICADO'

  return (
    <PublicDocumentLayout title={`Vista — ${doc.tipo_documento ?? 'Evaluación de Recuperación'}`}>
      <div className="print:hidden mb-6 rounded-xl border border-slate-200 bg-white p-4 flex items-center gap-3 flex-wrap">
        <Link to="/profesor/requisitos" className="text-sm text-slate-500 hover:text-slate-700">
          ← Mis requisitos
        </Link>
        <span className="text-xs text-slate-300">|</span>
        <Badge label={doc.estado} variant={doc.estado} />
        {isPublicado ? (
          <span className="text-xs text-emerald-600">● Visible públicamente.</span>
        ) : (
          <span className="text-xs text-slate-500">Solo tú puedes verlo.</span>
        )}

        <div className="ml-auto flex gap-2 flex-wrap">
          {isPublicado && (
            <a
              href={`/publico/requisitos/${doc.id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button size="sm" variant="secondary">Ver pública ↗</Button>
            </a>
          )}
          <Button
            size="sm"
            variant="secondary"
            loading={editMut.isPending}
            onClick={onEditClick}
          >
            Editar
          </Button>
          <Button
            size="sm"
            variant="danger"
            loading={deleteMut.isPending}
            onClick={onDeleteClick}
          >
            Eliminar
          </Button>
        </div>
      </div>

      {apiError && (
        <div className="mb-4 print:hidden">
          <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>
        </div>
      )}

      <RequisitoArticle doc={doc} tituloOverride="Evaluación de Recuperación" />
    </PublicDocumentLayout>
  )
}
