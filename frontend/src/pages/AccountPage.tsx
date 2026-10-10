import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { apiDelete, apiGet, apiPost } from '@/lib/api'
import { goToLogin, useMe } from '@/lib/auth'
import type { User, Workspace } from '@/lib/types'

const CONFIRM_WORD = 'eliminar'

// Mi cuenta: mis datos, la contraseña y la opción de eliminar la cuenta.
export function AccountPage() {
  const me = useMe()
  const [confirmText, setConfirmText] = useState('')
  const workspaces = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => apiGet<Workspace[]>('/workspaces'),
  })
  // Lo mismo que comprueba la API: antes hay que transferir o archivar los espacios propios.
  const blocking = (workspaces.data ?? []).filter((w) => w.is_owner && !w.archived)
  const remove = useMutation({
    mutationFn: () => apiDelete('/auth/me'),
    onSuccess: goToLogin,
  })

  if (!me.data) return null
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Mi cuenta</CardTitle>
          <CardDescription>
            Si entras con Google, nombre, email y foto se actualizan desde Google cada vez que entras.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          {me.data.avatar_url && (
            <img src={me.data.avatar_url} alt="" className="size-12 rounded-full" referrerPolicy="no-referrer" />
          )}
          <div>
            <p className="font-medium">{me.data.name}</p>
            <p className="text-sm text-muted-foreground">{me.data.email}</p>
          </div>
        </CardContent>
      </Card>

      <PasswordCard user={me.data} />

      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle>Eliminar mi cuenta</CardTitle>
          <CardDescription>
            Se borran tu nombre, tu email y tu foto, y sales de todos tus espacios. Las horas que
            registraste siguen en los informes de esos espacios, a nombre de «Usuario eliminado».
            No se puede deshacer: si vuelves a entrar, empezarás de cero. Más detalles
            en <Link to="/privacidad" className="underline">Privacidad</Link>.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {blocking.length > 0 ? (
            <div className="text-sm">
              <p>Antes tienes que transferir o archivar los espacios de los que eres dueño:</p>
              <ul className="mt-1 list-disc pl-5">
                {blocking.map((w) => (
                  <li key={w.id}>
                    <Link to={`/w/${w.id}/equipo`} className="underline">
                      {w.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <form
              className="flex flex-wrap items-center gap-2"
              onSubmit={(event) => {
                event.preventDefault()
                remove.mutate()
              }}
            >
              <Input
                className="max-w-64"
                value={confirmText}
                placeholder={`Escribe «${CONFIRM_WORD}» para confirmar`}
                onChange={(e) => setConfirmText(e.target.value)}
              />
              <Button
                type="submit"
                variant="destructive"
                disabled={confirmText.trim().toLowerCase() !== CONFIRM_WORD || remove.isPending}
              >
                Eliminar mi cuenta
              </Button>
            </form>
          )}
          {remove.isError && <p className="text-sm text-destructive">{remove.error.message}</p>}
        </CardContent>
      </Card>
    </div>
  )
}

// Cambiar la contraseña, o ponerla por primera vez si la cuenta es solo de Google.
function PasswordCard({ user }: { user: User }) {
  const queryClient = useQueryClient()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const save = useMutation({
    mutationFn: () =>
      apiPost('/auth/password', {
        current_password: user.has_password ? current : null,
        new_password: next,
      }),
    onSuccess: () => {
      setCurrent('')
      setNext('')
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Contraseña</CardTitle>
        <CardDescription>
          {user.has_password
            ? 'Para cambiarla, escribe la actual y la nueva (mínimo 8 caracteres).'
            : 'Entras con Google. Si quieres, ponte también una contraseña para entrar con tu email.'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            save.mutate()
          }}
        >
          {user.has_password && (
            <Input
              type="password"
              className="max-w-56"
              value={current}
              placeholder="Contraseña actual"
              autoComplete="current-password"
              required
              onChange={(e) => setCurrent(e.target.value)}
            />
          )}
          <Input
            type="password"
            className="max-w-56"
            value={next}
            placeholder="Contraseña nueva"
            autoComplete="new-password"
            minLength={8}
            maxLength={128}
            required
            onChange={(e) => setNext(e.target.value)}
          />
          <Button type="submit" disabled={save.isPending || next.length < 8}>
            {user.has_password ? 'Cambiar' : 'Poner contraseña'}
          </Button>
        </form>
        {save.isSuccess && <p className="mt-2 text-sm text-muted-foreground">Contraseña guardada.</p>}
        {save.isError && <p className="mt-2 text-sm text-destructive">{save.error.message}</p>}
      </CardContent>
    </Card>
  )
}
