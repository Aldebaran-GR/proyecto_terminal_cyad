import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import ProtectedRoute from './auth/ProtectedRoute'
import RoleRoute from './auth/RoleRoute'
import AdminLayout from './layouts/AdminLayout'
import ProfesorLayout from './layouts/ProfesorLayout'
import Loading from './components/ui/Loading'

const HomePage = lazy(() => import('./pages/HomePage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))
const ComingSoonPage = lazy(() => import('./pages/ComingSoonPage'))
const AdminDashboardPage = lazy(() => import('./pages/admin/DashboardPage'))
const ProfesorDashboardPage = lazy(() => import('./pages/profesor/DashboardPage'))

// M8 — Admin: Catálogos
const DepartamentosPage = lazy(() => import('./pages/admin/catalogos/DepartamentosPage'))
const LicenciaturasPage = lazy(() => import('./pages/admin/catalogos/LicenciaturasPage'))
const PosgradosPage = lazy(() => import('./pages/admin/catalogos/PosgradosPage'))
const AreasPage = lazy(() => import('./pages/admin/catalogos/AreasPage'))
const UEAPage = lazy(() => import('./pages/admin/catalogos/UEAPage'))
const PeriodosPage = lazy(() => import('./pages/admin/catalogos/PeriodosPage'))

// M8 — Admin: Profesores
const ProfesoresPage = lazy(() => import('./pages/admin/profesores/ProfesoresPage'))

// M8 — Admin: Documentos
const CartasAdminPage = lazy(() => import('./pages/admin/documentos/CartasAdminPage'))
const RequisitosAdminPage = lazy(() => import('./pages/admin/documentos/RequisitosAdminPage'))

// M8 — Admin: Autoevaluación
const AutoevaluacionAdminPage = lazy(() => import('./pages/admin/autoevaluacion/AutoevaluacionAdminPage'))
const FormularioBuilderPage = lazy(() => import('./pages/admin/autoevaluacion/FormularioBuilderPage'))
const FormularioPreviewPage = lazy(() => import('./pages/admin/autoevaluacion/FormularioPreviewPage'))

// M8 — Admin: Reportes
const ReportesPage = lazy(() => import('./pages/admin/reportes/ReportesPage'))

// M7 — Profesor: Cartas Temáticas
const CartasListPage = lazy(() => import('./pages/profesor/cartas/CartasListPage'))
const CartaFormPage = lazy(() => import('./pages/profesor/cartas/CartaFormPage'))
const CartaPreviewPage = lazy(() => import('./pages/profesor/cartas/CartaPreviewPage'))

// M7 — Profesor: Requisitos de Recuperación
const RequisitosListPage = lazy(() => import('./pages/profesor/requisitos/RequisitosListPage'))
const RequisitoFormPage = lazy(() => import('./pages/profesor/requisitos/RequisitoFormPage'))
const RequisitoPreviewPage = lazy(() => import('./pages/profesor/requisitos/RequisitoPreviewPage'))

// M7 — Profesor: Autoevaluación
const AutoevaluacionListPage = lazy(() => import('./pages/profesor/autoevaluacion/AutoevaluacionListPage'))
const AutoevaluacionFormPage = lazy(() => import('./pages/profesor/autoevaluacion/AutoevaluacionFormPage'))

// Vistas públicas (sin auth)
const ExplorarPage = lazy(() => import('./pages/publico/ExplorarPage'))
const PublicCartaPage = lazy(() => import('./pages/publico/PublicCartaPage'))
const PublicRequisitoPage = lazy(() => import('./pages/publico/PublicRequisitoPage'))

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
    <Suspense fallback={<Loading fullscreen />}>
      <Routes>
        {/* Públicas (sin login) */}
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />

        {/* Vistas públicas de documentos publicados (sin login) */}
        <Route path="/publico/explorar/:tipo" element={<ExplorarPage />} />
        <Route path="/publico/cartas/:id" element={<PublicCartaPage />} />
        <Route path="/publico/requisitos/:id" element={<PublicRequisitoPage />} />

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
          <Route path="catalogos/posgrados" element={<PosgradosPage />} />
          <Route path="catalogos/areas" element={<AreasPage />} />
          <Route path="catalogos/uea" element={<UEAPage />} />
          <Route path="catalogos/periodos" element={<PeriodosPage />} />

          {/* Documentos */}
          <Route path="documentos/cartas" element={<CartasAdminPage />} />
          <Route path="documentos/requisitos" element={<RequisitosAdminPage />} />

          {/* Autoevaluación */}
          <Route path="autoevaluacion" element={<AutoevaluacionAdminPage />} />
          <Route path="autoevaluacion/:id" element={<FormularioBuilderPage />} />
          <Route path="autoevaluacion/:id/preview" element={<FormularioPreviewPage />} />

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
          <Route path="cartas/:id/preview" element={<CartaPreviewPage />} />

          {/* Requisitos de Recuperación */}
          <Route path="requisitos" element={<RequisitosListPage />} />
          <Route path="requisitos/nuevo" element={<RequisitoFormPage />} />
          <Route path="requisitos/:id" element={<RequisitoFormPage />} />
          <Route path="requisitos/:id/preview" element={<RequisitoPreviewPage />} />

          {/* Autoevaluación */}
          <Route path="autoevaluacion" element={<AutoevaluacionListPage />} />
          <Route path="autoevaluacion/:id" element={<AutoevaluacionFormPage />} />
        </Route>

        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
