/**
 * Lista de Cartas Temáticas del profesor autenticado.
 *
 * Tres acciones únicas por fila — independientes del estado del documento:
 *   • Ver      — abre la vista final (preview).
 *   • Editar   — si está PUBLICADO se despublica antes de abrir el editor.
 *   • Eliminar — si está PUBLICADO se despublica antes de eliminar (cascada
 *                en una sola operación desde el punto de vista del usuario).
 *
 * Esto deja la lista simple y consistente; el "publicar / despublicar" se
 * resuelve dentro de cada acción.
 */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCartas, deleteCarta, cambiarEstadoCarta } from '../../../api/documentos'
import { getPeriodosActivos } from '../../../api/catalogos'
import Button from '../../../components/ui/Button'
import Badge from '../../../components/ui/Badge'
import Table from '../../../components/ui/Table'
import EmptyState from '../../../components/ui/EmptyState'
import Alert from '../../../components/ui/Alert'
import Loading from '../../../components/ui/Loading'
import CollapsiblePeriodoCard from '../../../components/ui/CollapsiblePeriodoCard'
import { groupByPeriodo } from '../../../utils/groupByPeriodo'

export default function CartasListPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [apiError, setApiError] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['cartas'],
    queryFn: () => getCartas().then((r) => r.data),
  })

  const { data: activos } = useQuery({
    queryKey: ['periodos-activos'],
    queryFn: () => getPeriodosActivos().then((r) => r.data),
  })
  const periodoCartasActivo = activos?.cartas ?? null

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['cartas'] })
    qc.invalidateQueries({ queryKey: ['cartas', 'dashboard'] })
  }

  // Editar: despublica primero si hace falta y abre el formulario.
  const editMut = useMutation({
    mutationFn: async (row) => {
      if (row.estado === 'PUBLICADO') {
        await cambiarEstadoCarta(row.id, 'BORRADOR')
      }
      return row.id
    },
    onSuccess: (id) => {
      invalidate()
      navigate(`/profesor/cartas/${id}`)
    },
    onError: (e) => setApiError(e.response?.data?.detail || 'No se pudo abrir el editor.'),
  })

  // Eliminar: despublica primero si hace falta y luego elimina.
  const deleteMut = useMutation({
    mutationFn: async (row) => {
      if (row.estado === 'PUBLICADO') {
        await cambiarEstadoCarta(row.id, 'BORRADOR')
      }
      return deleteCarta(row.id)
    },
    onSuccess: invalidate,
    onError: (e) => setApiError(
      e.response?.data?.errors?.estado
      || e.response?.data?.detail
      || 'Error al eliminar la carta.'
    ),
  })

  const onEditClick = (row) => {
    if (row.estado === 'PUBLICADO') {
      if (!window.confirm(
        'Esta carta está PUBLICADA. Para editarla se despublicará primero ' +
        '(dejará de aparecer en /publico/cartas/' + row.id + '). ¿Continuar?'
      )) return
    }
    editMut.mutate(row)
  }

  const onDeleteClick = (row) => {
    const aviso = row.estado === 'PUBLICADO'
      ? 'Esta carta está PUBLICADA. Se despublicará y eliminará. ¿Continuar?'
      : '¿Eliminar esta carta temática? Esta acción no se puede deshacer.'
    if (window.confirm(aviso)) deleteMut.mutate(row)
  }

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
      className: 'text-right w-64',
      render: (_, row) => {
        // puede_editar_ahora viene del backend e integra estado BORRADOR y el
        // flag activo_cartas del periodo del documento.
        const periodoCerrado = row.puede_editar_ahora === false
        const tooltip = periodoCerrado ? 'Periodo cerrado' : undefined
        return (
        <div className="flex justify-end gap-2">
          <Link to={`/profesor/cartas/${row.id}/preview`}>
            <Button size="sm" variant="secondary">Ver</Button>
          </Link>
          <Button
            size="sm"
            variant="secondary"
            loading={editMut.isPending && editMut.variables?.id === row.id}
            disabled={periodoCerrado}
            title={tooltip}
            onClick={() => onEditClick(row)}
          >
            Editar
          </Button>
          <Button
            size="sm"
            variant="danger"
            loading={deleteMut.isPending && deleteMut.variables?.id === row.id}
            disabled={periodoCerrado}
            title={tooltip}
            onClick={() => onDeleteClick(row)}
          >
            Eliminar
          </Button>
        </div>
      )},
    },
  ]

  if (isLoading) return <Loading text="Cargando cartas..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Cartas Temáticas</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Documentos de planeación académica por UEA y grupo.
          </p>
        </div>
        {periodoCartasActivo ? (
          <Link to="/profesor/cartas/nueva">
            <Button>+ Nueva Carta</Button>
          </Link>
        ) : (
          <Button disabled title="El administrador no ha habilitado ningún periodo para Cartas Temáticas">
            + Nueva Carta
          </Button>
        )}
      </div>

      {apiError && (
        <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>
      )}

      {cartas.length === 0 ? (
        <EmptyState
          title="Sin cartas temáticas"
          description="Crea tu primera carta temática para el trimestre actual."
          action={
            periodoCartasActivo ? (
              <Link to="/profesor/cartas/nueva">
                <Button>+ Nueva Carta</Button>
              </Link>
            ) : (
              <Button disabled title="El administrador no ha habilitado ningún periodo para Cartas Temáticas">
                + Nueva Carta
              </Button>
            )
          }
        />
      ) : (
        <div className="space-y-3">
          {groupByPeriodo(cartas, periodoCartasActivo?.clave ?? null).map((g) => (
            <CollapsiblePeriodoCard
              key={g.clave}
              clave={g.clave}
              fechaInicio={g.fechaInicio}
              count={g.rows.length}
              isActivo={g.isActivo}
            >
              <Table columns={columns} data={g.rows} emptyText="Sin cartas" />
            </CollapsiblePeriodoCard>
          ))}
        </div>
      )}
    </div>
  )
}
