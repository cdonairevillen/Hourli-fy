import { useQueryClient } from '@tanstack/react-query'
import { Link, Route, Routes } from 'react-router'
import { Button } from '@/components/ui/button'
import { apiPost } from '@/lib/api'
import { useMe } from '@/lib/auth'
import { InvitePage } from '@/pages/InvitePage'
import { LoginPage } from '@/pages/LoginPage'
import { WorkspacePage } from '@/pages/WorkspacePage'
import { WorkspacesPage } from '@/pages/WorkspacesPage'

function App() {
  return (
    <Routes>
      {/* La invitación es pública: gestiona ella misma si hay sesión o no. */}
      <Route path="/invite/:token" element={<InvitePage />} />
      <Route path="*" element={<PrivateApp />} />
    </Routes>
  )
}

// Todo lo demás exige sesión: sin ella se muestra el login.
function PrivateApp() {
  const me = useMe()
  const queryClient = useQueryClient()

  if (me.isLoading) return null
  if (me.isError) {
    return <p className="p-6 text-destructive">No se puede contactar con la API: {me.error.message}</p>
  }
  if (!me.data) return <LoginPage />

  async function logout() {
    await apiPost('/auth/logout')
    // Fuera toda la caché: la siguiente persona no debe ver datos de la anterior.
    queryClient.clear()
    queryClient.setQueryData(['me'], null)
  }

  return (
    <div className="mx-auto flex min-h-svh max-w-3xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <Link to="/" className="text-lg font-bold">
          Hourli-fy
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">{me.data.name}</span>
          <Button variant="outline" size="sm" onClick={logout}>
            Salir
          </Button>
        </div>
      </header>
      <Routes>
        <Route path="/" element={<WorkspacesPage />} />
        <Route path="/w/:wid" element={<WorkspacePage />} />
        <Route path="*" element={<p>Página no encontrada.</p>} />
      </Routes>
    </div>
  )
}

export default App
