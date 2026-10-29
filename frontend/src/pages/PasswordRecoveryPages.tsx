import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { apiPost } from '@/lib/api'
import type { User } from '@/lib/types'

// "Recuperar contraseña" en dos pasos, ambos públicos:
// 1. /recuperar: escribes tu email y te llega un link (caduca en 1 hora, un solo uso).
// 2. /recuperar/:token: el link del email; eliges contraseña nueva y entras.

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const send = useMutation({
    mutationFn: () => apiPost('/auth/password/forgot', { email }),
  })

  return (
    <RecoveryLayout
      title="Recuperar contraseña"
      description="Te enviaremos un link para elegir una contraseña nueva."
    >
      {send.isSuccess ? (
        <p className="text-sm">
          Si <strong>{email}</strong> tiene cuenta, te hemos enviado un email con el link. Mira
          también en spam. El link caduca en 1 hora.
        </p>
      ) : (
        <form
          className="flex flex-col gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            send.mutate()
          }}
        >
          <Input
            type="email"
            value={email}
            placeholder="Tu email"
            autoComplete="email"
            required
            onChange={(e) => setEmail(e.target.value)}
          />
          {send.isError && <p className="text-sm text-destructive">{send.error.message}</p>}
          <Button type="submit" disabled={send.isPending}>
            Enviar link
          </Button>
        </form>
      )}
    </RecoveryLayout>
  )
}

export function ResetPasswordPage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const reset = useMutation({
    mutationFn: () => apiPost<User>('/auth/password/reset', { token, password }),
    onSuccess: (user) => {
      // El reset ya abre la sesión: directo a la app.
      queryClient.setQueryData(['me'], user)
      navigate('/')
    },
  })
  const mismatch = repeat !== '' && repeat !== password

  return (
    <RecoveryLayout title="Contraseña nueva" description="Mínimo 8 caracteres.">
      <form
        className="flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          reset.mutate()
        }}
      >
        <Input
          type="password"
          value={password}
          placeholder="Contraseña nueva"
          autoComplete="new-password"
          minLength={8}
          maxLength={128}
          required
          onChange={(e) => setPassword(e.target.value)}
        />
        <Input
          type="password"
          value={repeat}
          placeholder="Repítela"
          autoComplete="new-password"
          required
          onChange={(e) => setRepeat(e.target.value)}
        />
        {mismatch && <p className="text-xs text-destructive">No coinciden.</p>}
        {reset.isError && (
          <p className="text-sm text-destructive">
            {reset.error.message}{' '}
            <Link to="/recuperar" className="underline">
              Pedir otro link
            </Link>
          </p>
        )}
        <Button type="submit" disabled={reset.isPending || mismatch || password.length < 8}>
          Guardar y entrar
        </Button>
      </form>
    </RecoveryLayout>
  )
}

function RecoveryLayout({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {children}
          <Link to="/" className="text-xs text-muted-foreground hover:underline">
            ← Volver a entrar
          </Link>
        </CardContent>
      </Card>
    </main>
  )
}
