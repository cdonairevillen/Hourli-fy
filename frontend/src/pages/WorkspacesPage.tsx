import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { apiGet, apiPost } from '@/lib/api'
import type { Workspace } from '@/lib/types'

const MAX_OWNED = 5

// Mis espacios (propios e invitados) y el formulario para crear uno nuevo.
export function WorkspacesPage() {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const workspaces = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => apiGet<Workspace[]>('/workspaces'),
  })
  const create = useMutation({
    mutationFn: (newName: string) => apiPost<Workspace>('/workspaces', { name: newName }),
    onSuccess: () => {
      setName('')
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })

  const list = workspaces.data ?? []
  const active = list.filter((w) => !w.archived)
  const archived = list.filter((w) => w.archived)
  const owned = active.filter((w) => w.is_owner).length

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Nuevo espacio</CardTitle>
          <CardDescription>
            Un espacio por estudio o equipo. Tienes {owned} de {MAX_OWNED} propios.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="flex gap-2"
            onSubmit={(event) => {
              event.preventDefault()
              if (name.trim()) create.mutate(name.trim())
            }}
          >
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Nombre del espacio"
              maxLength={80}
            />
            <Button type="submit" disabled={create.isPending || owned >= MAX_OWNED}>
              Crear
            </Button>
          </form>
          {create.isError && <p className="mt-2 text-sm text-destructive">{create.error.message}</p>}
        </CardContent>
      </Card>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">Mis espacios</h2>
        {workspaces.isLoading && <p className="text-muted-foreground">Cargando…</p>}
        {workspaces.isError && <p className="text-destructive">{workspaces.error.message}</p>}
        {workspaces.isSuccess && active.length === 0 && (
          <p className="text-muted-foreground">
            Aún no estás en ningún espacio. Crea uno o abre un link de invitación.
          </p>
        )}
        {active.map((workspace) => (
          <WorkspaceRow key={workspace.id} workspace={workspace} />
        ))}
      </section>

      {archived.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold text-muted-foreground">Archivados</h2>
          {archived.map((workspace) => (
            <WorkspaceRow key={workspace.id} workspace={workspace} />
          ))}
        </section>
      )}
    </div>
  )
}

function WorkspaceRow({ workspace }: { workspace: Workspace }) {
  return (
    <Link
      to={`/w/${workspace.id}`}
      className="flex items-center justify-between rounded-lg border p-4 hover:bg-accent"
    >
      <span className="font-medium">{workspace.name}</span>
      <Badge variant={workspace.is_owner ? 'default' : 'secondary'}>
        {workspace.is_owner ? 'Dueño' : 'Miembro'}
      </Badge>
    </Link>
  )
}
