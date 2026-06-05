import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const navItems = [
  {
    label: 'Dashboard',
    to: '/admin',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
    end: true,
  },
  {
    label: 'Profesores',
    to: '/admin/profesores',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
  {
    group: 'Catálogos',
    items: [
      { label: 'Departamentos', to: '/admin/catalogos/departamentos' },
      { label: 'Licenciaturas', to: '/admin/catalogos/licenciaturas' },
      { label: 'UEA', to: '/admin/catalogos/uea' },
      { label: 'Periodos', to: '/admin/catalogos/periodos' },
    ],
  },
  {
    group: 'Documentos',
    items: [
      { label: 'Cartas Temáticas', to: '/admin/documentos/cartas' },
      { label: 'Requisitos de Rec.', to: '/admin/documentos/requisitos' },
    ],
  },
  {
    label: 'Autoevaluación',
    to: '/admin/autoevaluacion',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    label: 'Reportes',
    to: '/admin/reportes',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
]

const linkCls = ({ isActive }) =>
  [
    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
    isActive
      ? 'bg-indigo-700 text-white font-medium'
      : 'text-slate-300 hover:bg-slate-700 hover:text-white',
  ].join(' ')

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-slate-100">
      {/* Sidebar */}
      <aside className="flex w-64 shrink-0 flex-col bg-slate-800">
        {/* Logo */}
        <div className="border-b border-slate-700 px-4 py-5">
          <p className="text-xs font-semibold uppercase tracking-widest text-indigo-400">
            CyAD · UAM-A
          </p>
          <p className="mt-0.5 text-sm font-semibold text-white">
            Proyecto Terminal
          </p>
          <span className="mt-1 inline-block rounded-full bg-indigo-600 px-2 py-0.5 text-xs font-medium text-white">
            Administrador
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {navItems.map((item, i) =>
            item.group ? (
              <div key={i} className="pt-4 first:pt-0">
                <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  {item.group}
                </p>
                {item.items.map((sub) => (
                  <NavLink key={sub.to} to={sub.to} className={linkCls}>
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
                    {sub.label}
                  </NavLink>
                ))}
              </div>
            ) : (
              <NavLink key={item.to} to={item.to} end={item.end} className={linkCls}>
                {item.icon}
                {item.label}
              </NavLink>
            )
          )}
        </nav>

        {/* Footer — usuario + logout */}
        <div className="border-t border-slate-700 px-4 py-4">
          <p className="truncate text-sm font-medium text-white">{user?.nombre}</p>
          <p className="truncate text-xs text-slate-400">{user?.email}</p>
          <button
            onClick={handleLogout}
            className="mt-3 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
