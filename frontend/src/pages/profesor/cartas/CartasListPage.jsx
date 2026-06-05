/**
 * Lista de Cartas Temáticas del profesor autenticado.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCartas, deleteCarta, cambiarEstadoCarta } from '../../../api/documentos'
import Button from '../../../components/ui/Button'
import Badge from '../../../components/ui/Badge'
import Table from '../../../components/ui/Table'
import EmptyState from '../../../components/ui/EmptyState'
import Alert from '../../../components/ui/Alert'
import Loading from '../../../components/ui/Loading'

const SIGUIENTE_ESTADO = { BORRADOR: 'PUBLICADO', PUBLICADO: 'ENVIADO' }
const LABEL_ESTADO = { PUBLICADO: 'Publicar', ENVIADO: 'Enviar' }

export default function CartasListPage() {
  const qc = useQueryClient()
  const [apiError, setApiError] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['cartas'],
    queryFn: () => getCartas().then((r) => r.data),
  })

  const deleteMut = useMutation({
    mutationFn: (id) => deleteCarta(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cartas'] }),
    onError: (e) =>
      setApiError(e.response?.data?.errors?.estado || 'Error al eliminar la carta.'),
  })

  const estadoMut = useMutation({
    mutationFn: ({ id, estado }) => cambiarEstadoCarta(id, estado),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cartas'] }),
    onError: (e) =>
      setApiError(e.response?.data?.detail || 'Error al cambiar el estado.'),
  })

  const cartas = data?.results ?? data ?? []

  const columns = [
    {
      key: 'uea_nombre',
      label: 'UEA',
      render: (val, row) => (
        <div>
          <p className="font-medium">{val}</p>
          <p className="text-xs text-slate-400">{row.periodo_clave}</p>
        </div>
      ),
    },
    {
      key: 'nombre_grupo',
      label: 'Grupo',
      render: (val, row) => (
        <div>
          <p>{val}</p>
          <p className="text-xs text-slate-400">ID: {row.id_grupo}</p>
        </div>
      ),
    },
    { key: 'horario', label: 'Horario' },
    {
      key: 'estado',
      label: 'Estado',
      render: (val) => <Badge label={val} variant={val} />,
    },
    {
      key: 'actions',
      label: '',
      className: 'text-right w-56',
      render: (_, row) => (
        <div className="flex justify-end gap-2">
          {row.estado !== 'ENVIADO' && (
            <Link to={`/profesor/cartas/${row.id}`}>
              <Button size="sm" variant="secondary">Editar</Button>
            </Link>
          )}
          {SIGUIENTE_ESTADO[row.estado] && (
            <Button
              size="sm"
              variant={row.estado === 'PUBLICADO' ? 'primary' : 'secondary'}
              loading={estadoMut.isPending}
              onClick={() =>
                estadoMut.mutate({ id: row.id, estado: SIGUIENTE_ESTADO[row.estado] })
              }
            >
              {LABEL_ESTADO[SIGUIENTE_ESTADO[row.estado]]}
            </Button>
          )}
          {row.estado === 'BORRADOR' && (
            <Button
              size="sm"
              variant="danger"
              loading={deleteMut.isPending}
              onClick={() => {
                if (window.confirm('¿Eliminar esta carta temática?')) {
                  deleteMut.mutate(row.id)
                }
              }}
            >
              Eliminar
            </Button>
          )}
        </div>
      ),
    },
  ]

  if (isLoading) return <Loading text="Cargando cartas..." />

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Cartas Temáticas</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Documentos de planeación académica por UEA y grupo.
          </p>
        </div>
        <Link to="/profesor/cartas/nueva">
          <Button>+ Nueva Carta</Button>
        </Link>
      </div>

      {apiError && (
        <Alert type="error" onClose={() => setApiError(null)}>
          {apiError}
        </Alert>
      )}

      {cartas.length === 0 ? (
        <EmptyState
          title="Sin cartas temáticas"
          description="Crea tu primera carta temática para el trimestre actual."
          action={
            <Link to="/profesor/cartas/nueva">
              <Button>+ Nueva Carta</Button>
            </Link>
          }
        />
      ) : (
        <Table columns={columns} data={cartas} emptyText="Sin cartas" />
      )}
    </div>
  )
}
