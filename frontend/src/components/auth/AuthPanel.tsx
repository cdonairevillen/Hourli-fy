import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { GoogleLoginButton } from '@/components/GoogleLoginButton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { apiPost } from '@/lib/api'
import { GOOGLE_ENABLED } from '@/lib/auth'
import type { User } from '@/lib/types'

const MIN_PASSWORD = 8

// Entrar o crear cuenta con email y contraseña (cualquier dominio), y Google como opción extra.
// Al terminar guarda el usuario en la caché de ['me'], y la página que lo usa reacciona sola.
export function AuthPanel() {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const submit = useMutation({
    mutationFn: () =>
      mode === 'login'
        ? apiPost<User>('/auth/login', { email, password })
        : apiPost<User>('/auth/register', { name, email, password }),
    onSuccess: (user) => queryClient.setQueryData(['me'], user),
  })
  const tooShort = mode === 'register' && password.length > 0 && password.length < MIN_PASSWORD

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="grid grid-cols-2 gap-1 rounded-lg bg-muted p-1">
        {(['login', 'register'] as const).map((value) => (
          <Button
            key={value}
            type="button"
            size="sm"
            variant={mode === value ? 'default' : 'ghost'}
            onClick={() => {
              setMode(value)
              submit.reset()
            }}
          >
            {value === 'login' ? 'Entrar' : 'Crear cuenta'}
          </Button>
        ))}
      </div>

      <form
        className="flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          submit.mutate()
        }}
      >
        {mode === 'register' && (
          <Input
            value={name}
            maxLength={80}
            placeholder="Tu nombre"
            autoComplete="name"
            required
            onChange={(e) => setName(e.target.value)}
          />
        )}
        <Input
          type="email"
          value={email}
          placeholder="Email (Gmail, Hotmail, Outlook, el que uses)"
          autoComplete="email"
          required
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          type="password"
          value={password}
          placeholder={mode === 'register' ? `Contraseña (mínimo ${MIN_PASSWORD} caracteres)` : 'Contraseña'}
          autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
          minLength={mode === 'register' ? MIN_PASSWORD : undefined}
          maxLength={128}
          required
          onChange={(e) => setPassword(e.target.value)}
        />
        {tooShort && (
          <p className="text-xs text-muted-foreground">Mínimo {MIN_PASSWORD} caracteres.</p>
        )}
        {submit.isError && <p className="text-sm text-destructive">{submit.error.message}</p>}
        <Button type="submit" disabled={submit.isPending || tooShort}>
          {mode === 'login' ? 'Entrar' : 'Crear cuenta'}
        </Button>
        {mode === 'login' && (
          <Link to="/recuperar" className="self-center text-xs text-muted-foreground hover:underline">
            ¿Olvidaste tu contraseña?
          </Link>
        )}
      </form>

      {GOOGLE_ENABLED && (
        <>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="h-px flex-1 bg-border" />o<span className="h-px flex-1 bg-border" />
          </div>
          <GoogleLoginButton />
        </>
      )}
    </div>
  )
}
