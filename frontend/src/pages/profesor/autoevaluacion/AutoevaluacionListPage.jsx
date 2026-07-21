/**
 * Lista de formularios de autoevaluación disponibles para el profesor.
 */
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getFormulariosDisponibles } from '../../../api/autoevaluacion'
import { getPeriodosActivos } from '../../../api/catalogos'
import Loading from '../../../components/ui/Loading'
import EmptyState from '../../../components/ui/EmptyState'
import Button from '../../../components/ui/Button'
import CollapsiblePeriodoCard from '../../../components/ui/CollapsiblePeriodoCard'
import { groupByPeriodo } from '../../../utils/groupByPeriodo'

function EstadoRespuestaBadge({ yaRespondido, respuestaEstado, formularioEstado, periodoAbierto }) {
  if (!periodoAbierto && yaRespondido) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
        Periodo cerrado — solo consulta
      </span>
    )
  }
  if (formularioEstado === 'CERRADO' && !yaRespondido) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-medium text-slate-700">
        Cerrado
      </span>
    )
  }
  if (yaRespondido) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
        <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
        Respondido
      </span>
    )
  }
  if (respuestaEstado === 'BORRADOR') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700">
        <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
            clipRule="evenodd"
          />
        </svg>
        En progreso
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
      Pendiente
    </span>
  )
}

export default function AutoevaluacionListPage() {
  // Polling cada 15 s para que el profesor vea, sin recargar, los
  // formularios que el admin publica o cierra desde otra sesión.
  const { data, isLoading } = useQuery({
    queryKey: ['formularios-disponibles'],
    queryFn: () => getFormulariosDisponibles().then((r) => r.data),
    refetchInterval: 15_000,
  })

  const { data: activos } = useQuery({
    queryKey: ['periodos-activos'],
    queryFn: () => getPeriodosActivos().then((r) => r.data),
  })
  const periodoAutoevalActivo = activos?.autoevaluacion ?? null

  const formularios = data?.results ?? data ?? []

  if (isLoading) return <Loading text="Cargando formularios..." />

  const renderFormulario = (f) => (
    <div
      key={f.id}
      className="rounded-xl border border-slate-200 bg-white p-5 space-y-3"
    >
      <div className="flex items-start justify-between gap-2">
        <h2 className="font-semibold text-slate-900">{f.titulo}</h2>
        <EstadoRespuestaBadge
          yaRespondido={f.ya_respondido}
          respuestaEstado={f.respuesta_estado}
          formularioEstado={f.estado}
          periodoAbierto={f.periodo_abierto}
        />
      </div>

      {f.descripcion && (
        <p className="text-sm text-slate-500 line-clamp-2">{f.descripcion}</p>
      )}

      <div className="flex flex-wrap gap-3 text-xs text-slate-500">
        <span>❓ {f.total_preguntas} preguntas</span>
        {f.version > 1 && (
          <span className="text-amber-600 font-medium">
            ⚠ Versión {f.version} — actualizado
          </span>
        )}
      </div>

      <div className="pt-1">
        {f.ya_respondido ? (
          <Link to={`/profesor/autoevaluacion/${f.id}`}>
            <Button variant="secondary" size="sm" className="w-full">
              Ver resultado
            </Button>
          </Link>
        ) : f.periodo_abierto === false ? (
          <Button size="sm" disabled className="w-full">
            Periodo cerrado
          </Button>
        ) : f.estado === 'CERRADO' ? (
          <Button size="sm" disabled className="w-full">
            Ya no acepta respuestas
          </Button>
        ) : (
          <Link to={`/profesor/autoevaluacion/${f.id}`}>
            <Button size="sm" className="w-full">
              {f.respuesta_estado === 'BORRADOR' ? 'Continuar' : 'Responder'}
            </Button>
          </Link>
        )}
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Autoevaluación</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Formularios de autoevaluación docente agrupados por periodo.
        </p>
      </div>

      {formularios.length === 0 ? (
        <EmptyState
          title="Sin formularios disponibles"
          description="El administrador aún no ha publicado formularios de autoevaluación."
        />
      ) : (
        <div className="space-y-3">
          {groupByPeriodo(formularios, periodoAutoevalActivo?.clave ?? null).map((g) => (
            <CollapsiblePeriodoCard
              key={g.clave}
              clave={g.clave}
              fechaInicio={g.fechaInicio}
              count={g.rows.length}
              isActivo={g.isActivo}
            >
              <div className="grid gap-4 sm:grid-cols-2">
                {g.rows.map(renderFormulario)}
              </div>
            </CollapsiblePeriodoCard>
          ))}
        </div>
      )}
    </div>
  )
}
