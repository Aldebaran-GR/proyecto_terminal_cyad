import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './auth/ProtectedRoute'
import RoleRoute from './auth/RoleRoute'
import AdminLayout from './layouts/AdminLayout'
import ProfesorLayout from './layouts/ProfesorLayout'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import ComingSoonPage from './pages/ComingSoonPage'
import AdminDashboardPage from './pages/admin/DashboardPage'
import ProfesorDashboardPage from './pages/profesor/DashboardPage'

// M8 — Admin: Catálogos
import DepartamentosPage from './pages/admin/catalogos/DepartamentosPage'
import LicenciaturasPage from './pages/admin/catalogos/LicenciaturasPage'
import UEAPage from './pages/admin/catalogos/UEAPage'
import PeriodosPage from './pages/admin/catalogos/PeriodosPage'

// M8 — Admin: Profesores
import ProfesoresPage from './pages/admin/profesores/ProfesoresPage'

// M8 — Admin: Documentos
import CartasAdminPage from './pages/admin/documentos/CartasAdminPage'
import RequisitosAdminPage from './pages/admin/documentos/RequisitosAdminPage'

// M8 — Admin: Autoevaluación
import AutoevaluacionAdminPage from './pages/admin/autoevaluacion/AutoevaluacionAdminPage'
import FormularioBuilderPage from './pages/admin/autoevaluacion/FormularioBuilderPage'

// M8 — Admin: Reportes
import ReportesPage from './pages/admin/reportes/ReportesPage'

// M7 — Profesor: Cartas Temáticas
import CartasListPage from './pages/profesor/cartas/CartasListPage'
import CartaFormPage from './pages/profesor/cartas/CartaFormPage'

// M7 — Profesor: Requisitos de Recuperación
import RequisitosListPage from './pages/profesor/requisitos/RequisitosListPage'
import RequisitoFormPage from './pages/profesor/requisitos/RequisitoFormPage'

// M7 — Profesor: Autoevaluación
import AutoevaluacionListPage from './pages/profesor/autoevaluacion/AutoevaluacionListPage'
import AutoevaluacionFormPage from './pages/profesor/autoevaluacion/AutoevaluacionFormPage'

/* ─── Wrapper helper ─────────────────────────────────────── */
function AdminRoute({ children }) {
  return (
    <ProtectedRoute>
      <RoleRoute role="ADMIN">{children}</RoleRoute>
    </ProtectedRoute>
  )
}

function ProfesorRoute({ children }) {
  return (
    <ProtectedRoute>
      <RoleRoute role="PROFESOR">{children}</RoleRoute>
    </ProtectedRoute>
  )
}

export default function App() {
  return (
    <Routes>
      {/* Pública */}
      <Route path="/login" element={<LoginPage />} />

      {/* ── Admin ──────────────────────────────────────────── */}
      <Route
        path="/admin"
        element={
          <AdminRoute>
            <AdminLayout />
          </AdminRoute>
        }
      >
        <Route index element={<AdminDashboardPage />} />

        {/* Profesores */}
        <Route path="profesores" element={<ProfesoresPage />} />

        {/* Catálogos */}
        <Route path="catalogos/departamentos" element={<DepartamentosPage />} />
        <Route path="catalogos/licenciaturas" element={<LicenciaturasPage />} />
        <Route path="catalogos/uea" element={<UEAPage />} />
        <Route path="catalogos/periodos" element={<PeriodosPage />} />

        {/* Documentos */}
        <Route path="documentos/cartas" element={<CartasAdminPage />} />
        <Route path="documentos/requisitos" element={<RequisitosAdminPage />} />

        {/* Autoevaluación */}
        <Route path="autoevaluacion" element={<AutoevaluacionAdminPage />} />
        <Route path="autoevaluacion/:id" element={<FormularioBuilderPage />} />

        {/* Reportes */}
        <Route path="reportes" element={<ReportesPage />} />
      </Route>

      {/* ── Profesor ───────────────────────────────────────── */}
      <Route
        path="/profesor"
        element={
          <ProfesorRoute>
            <ProfesorLayout />
          </ProfesorRoute>
        }
      >
        <Route index element={<ProfesorDashboardPage />} />

        {/* Cartas Temáticas */}
        <Route path="cartas" element={<CartasListPage />} />
        <Route path="cartas/nueva" element={<CartaFormPage />} />
        <Route path="cartas/:id" element={<CartaFormPage />} />

        {/* Requisitos de Recuperación */}
        <Route path="requisitos" element={<RequisitosListPage />} />
        <Route path="requisitos/nuevo" element={<RequisitoFormPage />} />
        <Route path="requisitos/:id" element={<RequisitoFormPage />} />

        {/* Autoevaluación */}
        <Route path="autoevaluacion" element={<AutoevaluacionListPage />} />
        <Route path="autoevaluacion/:id" element={<AutoevaluacionFormPage />} />
      </Route>

      {/* Raíz → login */}
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
