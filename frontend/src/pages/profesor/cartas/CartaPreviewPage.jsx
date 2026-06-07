/**
 * Vista previa de una Carta Temática — muestra el documento como se verá
 * públicamente, con barra superior de acciones.
 *
 * Acciones (consistentes con la lista):
 *   • Editar   — si está PUBLICADO se despublica primero, luego abre el editor.
 *   • Eliminar — si está PUBLICADO se despublica primero, luego elimina.
 *   • Ver pública ↗ — solo si está PUBLICADO, abre la URL pública en pestaña nueva.
 */
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCarta, deleteCarta, cambiarEstadoCarta } from '../../../api/documentos'
import Button from '../../../components/ui/Button'
import Alert from '../../../components/ui/Alert'
import Badge from '../../../components/ui/Badge'
import Loading from '../../../components/ui/Loading'
import PublicDocumentLayout from '../../publico/PublicDocumentLayout'
import { CartaTematicaArticle } from '../../publico/DocumentArticles'

export default function CartaPreviewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [apiError, setApiError] = useState(null)

  const { data: carta, isLoading } = useQuery({
    queryKey: ['carta', id],
    queryFn: () => getCarta(id).then((r) => r.data),
  })

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['carta', id] })
    qc.invalidateQueries({ queryKey: ['cartas'] })
    qc.invalidateQueries({ queryKey: ['cartas', 'dashboard'] })
  }
  const onError = (e) =>
    setApiError(
      e.response?.data?.detail
      || e.response?.data?.errors?.estado
      || 'Error.'
    )

  // Editar — despublica si hace falta y navega al editor.
  const editMut = useMutation({
    mutationFn: async () => {
      if (carta?.estado === 'PUBLICADO') {
        await cambiarEstadoCarta(id, 'BORRADOR')
      }
    },
    onSuccess: () => {
      invalidate()
      navigate(`/profesor/cartas/${id}`)
    },
    onError,
  })

  // Eliminar — despublica si hace falta y elimina.
  const deleteMut = useMutation({
    mutationFn: async () => {
      if (carta?.estado === 'PUBLICADO') {
        await cambiarEstadoCarta(id, 'BORRADOR')
      }
      return deleteCarta(id)
    },
    onSuccess: () => {
      invalidate()
      navigate('/profesor/cartas')
    },
    onError,
  })

  const onEditClick = () => {
    if (carta?.estado === 'PUBLICADO') {
      if (!window.confirm(
        'Esta carta está PUBLICADA. Para editarla se despublicará primero. ¿Continuar?'
      )) return
    }
    editMut.mutate()
  }
  const onDeleteClick = () => {
    const aviso = carta?.estado === 'PUBLICADO'
      ? 'Esta carta está PUBLICADA. Se despublicará y eliminará. ¿Continuar?'
      : '¿Eliminar esta carta temática? Esta acción no se puede deshacer.'
    if (window.confirm(aviso)) deleteMut.mutate()
  }

  if (isLoading) return <Loading text="Cargando vista previa..." />
  if (!carta) {
    return (
      <div className="p-8">
        <p className="text-sm text-slate-500">No se pudo cargar la carta.</p>
        <Link to="/profesor/cartas" className="text-indigo-600 text-sm hover:underline">
          ← Volver
        </Link>
      </div>
    )
  }

  const isPublicado = carta.estado === 'PUBLICADO'

  return (
    <PublicDocumentLayout title={`Vista — ${carta.tipo_documento ?? 'Carta Temática'}`}>
      {/* Barra de acciones (no aparece en impresión ni en la vista pública) */}
      <div className="print:hidden mb-6 rounded-xl border border-slate-200 bg-white p-4 flex items-center gap-3 flex-wrap">
        <Link to="/profesor/cartas" className="text-sm text-slate-500 hover:text-slate-700">
          ← Mis cartas
        </Link>
        <span className="text-xs text-slate-300">|</span>
        <Badge label={carta.estado} variant={carta.estado} />
        {isPublicado ? (
          <span className="text-xs text-emerald-600">● Visible públicamente.</span>
        ) : (
          <span className="text-xs text-slate-500">Solo tú puedes verla.</span>
        )}

        <div className="ml-auto flex gap-2 flex-wrap">
          {isPublicado && (
            <a
              href={`/publico/cartas/${carta.id}`}
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

      <CartaTematicaArticle carta={carta} tituloOverride="Carta Temática" />
    </PublicDocumentLayout>
  )
}
