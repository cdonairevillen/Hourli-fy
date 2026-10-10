import { Link, Route, Routes } from 'react-router'
import { TimerBar } from '@/components/entries/TimerBar'
import { Button } from '@/components/ui/button'
import { apiPost } from '@/lib/api'
import { goToLogin, useMe } from '@/lib/auth'
import { AccountPage } from '@/pages/AccountPage'
import { InvitePage } from '@/pages/InvitePage'
import { LoginPage } from '@/pages/LoginPage'
import { ForgotPasswordPage, ResetPasswordPage } from '@/pages/PasswordRecoveryPages'
import { PrivacyPage } from '@/pages/PrivacyPage'
import { ProjectSheetPage } from '@/pages/ProjectSheetPage'
import { WorkspacePage } from '@/pages/WorkspacePage'
import { WorkspacesPage } from '@/pages/WorkspacesPage'

function App() {
  return (
    <Routes>
      {/* La invitación es pública: gestiona ella misma si hay sesión o no. */}
      <Route path="/invite/:token" element={<InvitePage />} />
      {/* Privacidad también es pública: la enlaza la pantalla de consentimiento de Google. */}
      <Route path="/privacidad" element={<PrivacyPage />} />
      <Route path="/recuperar" element={<ForgotPasswordPage />} />
      <Route path="/recuperar/:token" element={<ResetPasswordPage />} />
      <Route path="*" element={<PrivateApp />} />
    </Routes>
  )
}

// Todo lo demás exige sesión: sin ella se muestra el login.
function PrivateApp() {
  const me = useMe()

  if (me.isLoading) return null
  if (me.isError) {
    return <p className="p-6 text-destructive">No se puede contactar con la API: {me.error.message}</p>
  }
  if (!me.data) return <LoginPage />

  async function logout() {
    await apiPost('/auth/logout')
    goToLogin()
  }

  return (
    <div className="mx-auto flex min-h-svh max-w-3xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <Link to="/" className="text-lg font-bold">
          Hourli-fy
        </Link>
        <div className="flex items-center gap-3">
          <TimerBar />
          {me.data.is_admin && (
            // El panel lo sirve la API (SQLAdmin), no React: enlace normal en otra pestaña.
            // En producción va directo a Cloud Run (VITE_ADMIN_URL); en local, al proxy de Vite.
            <a
              href={import.meta.env.VITE_ADMIN_URL || '/admin/'}
              target="_blank"
              rel="noreferrer"
              className="text-sm font-medium text-muted-foreground hover:underline"
            >
              Admin
            </a>
          )}
          <Link to="/cuenta" className="text-sm text-muted-foreground hover:underline">
            {me.data.name}
          </Link>
          <Button variant="outline" size="sm" onClick={logout}>
            Salir
          </Button>
        </div>
      </header>
      <Routes>
        <Route path="/" element={<WorkspacesPage />} />
        <Route path="/w/:wid" element={<WorkspacePage tab="projects" />} />
        <Route path="/w/:wid/hoja" element={<WorkspacePage tab="sheet" />} />
        <Route path="/w/:wid/panel" element={<WorkspacePage tab="panel" />} />
        <Route path="/w/:wid/catalogo" element={<WorkspacePage tab="catalog" />} />
        <Route path="/w/:wid/equipo" element={<WorkspacePage tab="team" />} />
        <Route path="/w/:wid/p/:pid" element={<ProjectSheetPage />} />
        <Route path="/cuenta" element={<AccountPage />} />
        <Route path="*" element={<p>Página no encontrada.</p>} />
      </Routes>
    </div>
  )
}

export default App
