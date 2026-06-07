import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../auth/AuthContext'
import { getCartas, getRequisitos } from '../../api/documentos'
import { getFormulariosDisponibles } from '../../api/autoevaluacion'
import Loading from '../../components/ui/Loading'
import Badge from '../../components/ui/Badge'
import { Link } from 'react-router-dom'

/**
 * Normaliza la respuesta de un endpoint paginado o sin paginar a un arreglo.
 * Evita el bug `items.slice is not a function` cuando otra vista compartía la
 * misma queryKey y dejaba el cache con forma de objeto paginado.
 */
const toArray = (data) =>
  Array.isArray(data)
    ? data
    : Array.isArray(data?.results)
      ? data.results
      : []

function SummaryCard({ title, to, items, emptyMsg, renderItem }) {
  const list = Array.isArray(items) ? items : []
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
        <Link to={to} className="text-xs text-indigo-600 hover:underline">Ver todos →</Link>
      </div>
      {list.length === 0 ? (
        <p className="text-sm text-slate-400 py-4 text-center">{emptyMsg}</p>
      ) : (
        <ul className="space-y-2">
          {list.slice(0, 3).map(renderItem)}
        </ul>
      )}
    </div>
  )
}

export default function ProfesorDashboardPage() {
  const { user } = useAuth()
  const nombre = user?.perfil_profesor?.nombre_completo ?? user?.nombre

  // queryKeys distintas de las listas (['cartas'], ['requisitos'], ['formularios-disponibles'])
  // para que la invalidación tras crear/responder un documento refresque sin colisionar.
  // Dashboard del profesor: refresca solo (sin recargar) al focar la pestaña
  // y cada 30 segundos por si el admin publicó algo en otra sesión.
  const { data: cartasData, isLoading: cartasLoading } = useQuery({
    queryKey: ['cartas', 'dashboard'],
    queryFn: () => getCartas({ page_size: 5 }).then((r) => toArray(r.data)),
    refetchInterval: 30_000,
  })

  const { data: requisitosData, isLoading: reqLoading } = useQuery({
    queryKey: ['requisitos', 'dashboard'],
    queryFn: () => getRequisitos({ page_size: 5 }).then((r) => toArray(r.data)),
    refetchInterval: 30_000,
  })

  const { data: formularios, isLoading: fLoading } = useQuery({
    queryKey: ['formularios-disponibles', 'dashboard'],
    queryFn: () => getFormulariosDisponibles().then((r) => toArray(r.data)),
    refetchInterval: 30_000,
  })

  const cartas = Array.isArray(cartasData) ? cartasData : []
  const requisitos = Array.isArray(requisitosData) ? requisitosData : []
  const forms = Array.isArray(formularios) ? formularios : []

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Mi Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Bienvenido, <span className="font-medium">{nombre}</span>
        </p>
      </div>

      {/* Resumen numérico */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Cartas Temáticas', value: cartas.length, to: '/profesor/cartas', color: 'text-indigo-600' },
          { label: 'Requisitos de Rec.', value: requisitos.length, to: '/profesor/requisitos', color: 'text-teal-600' },
          { label: 'Formularios pendientes', value: forms.filter(f => !f.ya_respondido).length, to: '/profesor/autoevaluacion', color: 'text-amber-600' },
        ].map((s) => (
          <Link key={s.to} to={s.to} className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200 hover:ring-indigo-300 transition-all block">
            <p className="text-sm text-slate-500">{s.label}</p>
            <p className={`mt-1 text-3xl font-bold ${s.color}`}>{s.value}</p>
          </Link>
        ))}
      </div>

      {/* Listas */}
      <div className="grid gap-6 md:grid-cols-2">
        {cartasLoading ? (
          <Loading />
        ) : (
          <SummaryCard
            title="Cartas Temáticas recientes"
            to="/profesor/cartas"
            items={cartas}
            emptyMsg="Aún no tienes cartas temáticas."
            renderItem={(carta) => (
              <li key={carta.id} className="flex items-center justify-between text-sm">
                <div>
                  <p className="font-medium text-slate-800">{carta.uea_nombre}</p>
                  <p className="text-xs text-slate-400">{carta.periodo_clave} · Grupo {carta.id_grupo}</p>
                </div>
                <Badge label={carta.estado} variant={carta.estado} />
              </li>
            )}
          />
        )}

        {reqLoading ? (
          <Loading />
        ) : (
          <SummaryCard
            title="Requisitos de Recuperación recientes"
            to="/profesor/requisitos"
            items={requisitos}
            emptyMsg="Aún no tienes requisitos de recuperación."
            renderItem={(req) => (
              <li key={req.id} className="flex items-center justify-between text-sm">
                <div>
                  <p className="font-medium text-slate-800">{req.uea_nombre}</p>
                  <p className="text-xs text-slate-400">{req.periodo_clave} · Grupo {req.id_grupo}</p>
                </div>
                <Badge label={req.estado} variant={req.estado} />
              </li>
            )}
          />
        )}
      </div>

      {/* Formularios disponibles */}
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-700">Formularios de Autoevaluación</h2>
          <Link to="/profesor/autoevaluacion" className="text-xs text-indigo-600 hover:underline">Ver todos →</Link>
        </div>
        {fLoading ? (
          <Loading />
        ) : forms.length === 0 ? (
          <p className="text-sm text-slate-400 py-4 text-center">No hay formularios disponibles en este momento.</p>
        ) : (
          <ul className="space-y-3">
            {forms.map((f) => (
              <li key={f.id} className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-800">{f.titulo}</p>
                  <p className="text-xs text-slate-400">{f.total_preguntas} preguntas · {f.periodo_clave}</p>
                </div>
                {f.ya_respondido ? (
                  <Badge label="Respondido" variant="ENVIADO" />
                ) : (
                  <Link
                    to={`/profesor/autoevaluacion/${f.id}`}
                    className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
                  >
                    Responder
                  </Link>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
