import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { apiPost } from '@/lib/api'
import { GOOGLE_CLIENT_ID } from '@/lib/auth'
import type { User } from '@/lib/types'

// Tipos mínimos de Google Identity Services (su script lo carga este componente).
type CredentialResponse = { credential: string }
type GoogleAccounts = {
  id: {
    initialize: (options: { client_id: string; callback: (r: CredentialResponse) => void }) => void
    renderButton: (element: HTMLElement, options: Record<string, string>) => void
  }
}
declare global {
  interface Window {
    google?: { accounts: GoogleAccounts }
  }
}

const CLIENT_ID = GOOGLE_CLIENT_ID
const SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

// Carga el script de Google una sola vez aunque haya varios botones.
let scriptPromise: Promise<void> | null = null
function loadGoogleScript(): Promise<void> {
  scriptPromise ??= new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = SCRIPT_SRC
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('No se pudo cargar el login de Google'))
    document.head.appendChild(script)
  })
  return scriptPromise
}

// Botón oficial "Iniciar sesión con Google". Google devuelve un ID token (credential),
// lo mandamos a la API, que lo verifica y nos deja la cookie de sesión.
export function GoogleLoginButton() {
  const container = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!CLIENT_ID) return
    let cancelled = false
    loadGoogleScript()
      .then(() => {
        if (cancelled || !container.current || !window.google) return
        window.google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: async ({ credential }) => {
            try {
              const user = await apiPost<User>('/auth/google', { credential })
              queryClient.setQueryData(['me'], user)
            } catch (e) {
              setError((e as Error).message)
            }
          },
        })
        window.google.accounts.id.renderButton(container.current, {
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          locale: 'es',
        })
      })
      .catch((e: Error) => setError(e.message))
    return () => {
      cancelled = true
    }
  }, [queryClient])

  return (
    <div className="flex flex-col items-center gap-2">
      <div ref={container} />
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}
