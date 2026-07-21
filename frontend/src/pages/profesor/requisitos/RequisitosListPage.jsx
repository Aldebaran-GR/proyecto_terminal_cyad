/**
 * Lista de Requisitos de Recuperación del profesor autenticado.
 *
 * Tres acciones únicas por fila — independientes del estado del documento:
 *   • Ver      — abre la vista final (preview).
 *   • Editar   — si está PUBLICADO se despublica antes de abrir el editor.
 *   • Eliminar — si está PUBLICADO se despublica antes de eliminar.
 */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getRequisitos, deleteRequisito, cambiarEstadoRequisito } from '../../../api/documentos'
import { getPeriodosActivos } from '../../../api/catalogos'
import { parseApiError } from '../../../utils/apiError'
import Button from '../../../components/ui/Button'
import Badge from '../../../components/ui/Badge'
import Table from '../../../components/ui/Table'
import EmptyState from '../../../components/ui/EmptyState'
import Alert from '../../../components/ui/Alert'
import Loading from '../../../components/ui/Loading'
import CollapsiblePeriodoCard from '../../../components/ui/CollapsiblePeriodoCard'
import { groupByPeriodo } from '../../../utils/groupByPeriodo'

export default function RequisitosListPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [apiError, setApiError] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['requisitos'],
    queryFn: () => getRequisitos().then((r) => r.data),
  })

  const { data: activos } = useQuery({
    queryKey: ['periodos-activos'],
    queryFn: () => getPeriodosActivos().then((r) => r.data),
  })
  const periodoRequisitosActivo = activos?.requisitos ?? null

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['requisitos'] })
    qc.invalidateQueries({ queryKey: ['requisitos', 'dashboard'] })
  }

  const editMut = useMutation({
    mutationFn: async (row) => {
      if (row.estado === 'PUBLICADO') {
        await cambiarEstadoRequisito(row.id, 'BORRADOR')
      }
      return row.id
    },
    onSuccess: (id) => {
      invalidate()
      navigate(`/profesor/requisitos/${id}`)
    },
    onError: (e) => setApiError(parseApiError(e.response?.data, 'No se pudo abrir el editor.')),
  })

  const deleteMut = useMutation({
    mutationFn: async (row) => {
      if (row.estado === 'PUBLICADO') {
        await cambiarEstadoRequisito(row.id, 'BORRADOR')
      }
      return deleteRequisito(row.id)
    },
    onSuccess: invalidate,
    onError: (e) => setApiError(parseApiError(e.response?.data, 'Error al eliminar el requisito.')),
  })

  const onEditClick = (row) => {
    if (row.estado === 'PUBLICADO') {
      if (!window.confirm(
        'Este requisito está PUBLICADO. Para editarlo se despublicará primero ' +
        '(dejará de aparecer en /publico/requisitos/' + row.id + '). ¿Continuar?'
      )) return
    }
    editMut.mutate(row)
  }

  const onDeleteClick = (row) => {
    const aviso = row.estado === 'PUBLICADO'
      ? 'Este requisito está PUBLICADO. Se despublicará y eliminará. ¿Continuar?'
      : '¿Eliminar este requisito? Esta acción no se puede deshacer.'
    if (window.confirm(aviso)) deleteMut.mutate(row)
  }

  const requisitos = data?.results ?? data ?? []

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
    {
      key: 'fecha_hora',
      label: 'Fecha / hora',
      render: (val) => val || <span className="text-slate-400">—</span>,
    },
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
        const periodoCerrado = row.puede_editar_ahora === false
        const tooltip = periodoCerrado ? 'Periodo cerrado' : undefined
        return (
        <div className="flex justify-end gap-2">
          <Link to={`/profesor/requisitos/${row.id}/preview`}>
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

  if (isLoading) return <Loading text="Cargando requisitos..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Requisitos de Recuperación</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Documentos de recuperación por UEA y grupo.
          </p>
        </div>
        {periodoRequisitosActivo ? (
          <Link to="/profesor/requisitos/nuevo">
            <Button>+ Nuevo Requisito</Button>
          </Link>
        ) : (
          <Button disabled title="El administrador no ha habilitado ningún periodo para Requisitos de Recuperación">
            + Nuevo Requisito
          </Button>
        )}
      </div>

      {apiError && (
        <Alert type="error" onClose={() => setApiError(null)}>{apiError}</Alert>
      )}

      {requisitos.length === 0 ? (
        <EmptyState
          title="Sin requisitos de recuperación"
          description="Crea tu primer documento de requisitos para el trimestre actual."
          action={
            periodoRequisitosActivo ? (
              <Link to="/profesor/requisitos/nuevo">
                <Button>+ Nuevo Requisito</Button>
              </Link>
            ) : (
              <Button disabled title="El administrador no ha habilitado ningún periodo para Requisitos de Recuperación">
                + Nuevo Requisito
              </Button>
            )
          }
        />
      ) : (
        <div className="space-y-3">
          {groupByPeriodo(requisitos, periodoRequisitosActivo?.clave ?? null).map((g) => (
            <CollapsiblePeriodoCard
              key={g.clave}
              clave={g.clave}
              fechaInicio={g.fechaInicio}
              count={g.rows.length}
              isActivo={g.isActivo}
            >
              <Table columns={columns} data={g.rows} emptyText="Sin requisitos" />
            </CollapsiblePeriodoCard>
          ))}
        </div>
      )}
    </div>
  )
}
