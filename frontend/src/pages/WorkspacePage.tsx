import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, NavLink, useNavigate, useParams } from 'react-router'
import { CategoriesCard } from '@/components/catalog/CategoriesCard'
import { ProjectsCard } from '@/components/catalog/ProjectsCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { apiDelete, apiGet, apiPatch, apiPost } from '@/lib/api'
import { useMe } from '@/lib/auth'
import type { Invitation, InvitationCreated, Member, Workspace } from '@/lib/types'

const STATUS_LABEL: Record<Invitation['status'], string> = {
  active: 'Activo',
  expired: 'Caducado',
  revoked: 'Revocado',
  exhausted: 'Agotado',
  archived: 'Espacio archivado',
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('es-ES', { timeZone: 'Europe/Madrid' })
}

// Gestión de un espacio en dos pestañas: "Equipo" (ajustes, miembros e invitaciones) y
// "Catálogo" (proyectos y labels). Lo que es solo del dueño se oculta a los miembros.
export function WorkspacePage({ tab }: { tab: 'team' | 'catalog' }) {
  const { wid = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const me = useMe()
  const workspaces = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => apiGet<Workspace[]>('/workspaces'),
  })
  const workspace = workspaces.data?.find((w) => w.id === wid)

  const update = useMutation({
    mutationFn: (body: Partial<Pick<Workspace, 'name' | 'archived' | 'owner_id'>>) =>
      apiPatch<Workspace>(`/workspaces/${wid}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      queryClient.invalidateQueries({ queryKey: ['members', wid] })
    },
  })
  const leave = useMutation({
    mutationFn: () => apiDelete(`/workspaces/${wid}/members/${me.data?.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      navigate('/')
    },
  })

  if (workspaces.isLoading) return <p className="text-muted-foreground">Cargando…</p>
  if (!workspace) {
    return (
      <p>
        Espacio no encontrado. <Link to="/" className="underline">Volver</Link>
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Link to="/" className="text-muted-foreground hover:underline">
            Espacios /
          </Link>
          <h1 className="text-xl font-semibold">{workspace.name}</h1>
          {workspace.archived && <Badge variant="secondary">Archivado</Badge>}
        </div>
        {!workspace.is_owner && (
          <Button
            variant="outline"
            disabled={leave.isPending}
            onClick={() => confirm('¿Salir de este espacio?') && leave.mutate()}
          >
            Salir del espacio
          </Button>
        )}
      </div>
      {(update.isError || leave.isError) && (
        <p className="text-sm text-destructive">{(update.error ?? leave.error)?.message}</p>
      )}

      <nav className="flex gap-1 border-b">
        <TabLink to={`/w/${wid}`}>Equipo</TabLink>
        <TabLink to={`/w/${wid}/catalogo`}>Catálogo</TabLink>
      </nav>

      {tab === 'team' && (
        <>
          {workspace.is_owner && (
            <SettingsCard workspace={workspace} onSave={(body) => update.mutate(body)} />
          )}
          <MembersCard
            workspace={workspace}
            meId={me.data?.id}
            onTransfer={(member) =>
              confirm(`¿Transferir el espacio a ${member.name}? Dejarás de ser el dueño.`) &&
              update.mutate({ owner_id: member.user_id })
            }
          />
          {workspace.is_owner && !workspace.archived && <InvitationsCard wid={wid} />}
        </>
      )}
      {tab === 'catalog' && (
        <>
          <ProjectsCard workspace={workspace} />
          <CategoriesCard workspace={workspace} />
        </>
      )}
    </div>
  )
}

function TabLink({ to, children }: { to: string; children: string }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `-mb-px border-b-2 px-3 py-2 text-sm ${isActive ? 'border-primary font-medium' : 'border-transparent text-muted-foreground hover:text-foreground'}`
      }
    >
      {children}
    </NavLink>
  )
}

function SettingsCard({
  workspace,
  onSave,
}: {
  workspace: Workspace
  onSave: (body: Partial<Pick<Workspace, 'name' | 'archived'>>) => void
}) {
  const [name, setName] = useState(workspace.name)
  return (
    <Card>
      <CardHeader>
        <CardTitle>Ajustes</CardTitle>
        <CardDescription>
          Archivar no borra nada: oculta el espacio, invalida sus links y libera uno de tus 5 huecos.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <form
          className="flex flex-1 gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            if (name.trim() && name.trim() !== workspace.name) onSave({ name: name.trim() })
          }}
        >
          <Input value={name} onChange={(event) => setName(event.target.value)} maxLength={80} />
          <Button type="submit" variant="outline">
            Renombrar
          </Button>
        </form>
        <Button
          variant={workspace.archived ? 'default' : 'destructive'}
          onClick={() => onSave({ archived: !workspace.archived })}
        >
          {workspace.archived ? 'Desarchivar' : 'Archivar'}
        </Button>
      </CardContent>
    </Card>
  )
}

function MembersCard({
  workspace,
  meId,
  onTransfer,
}: {
  workspace: Workspace
  meId: string | undefined
  onTransfer: (member: Member) => void
}) {
  const queryClient = useQueryClient()
  const members = useQuery({
    queryKey: ['members', workspace.id],
    queryFn: () => apiGet<Member[]>(`/workspaces/${workspace.id}/members`),
  })
  const expel = useMutation({
    mutationFn: (userId: string) => apiDelete(`/workspaces/${workspace.id}/members/${userId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['members', workspace.id] }),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Miembros</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {members.data?.map((member) => (
          <div key={member.user_id} className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <span className="font-medium">{member.name}</span>{' '}
              <span className="text-sm text-muted-foreground">{member.email}</span>
              {member.is_owner && <Badge className="ml-2">Dueño</Badge>}
            </div>
            {workspace.is_owner && member.user_id !== meId && (
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => onTransfer(member)}>
                  Hacer dueño
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => confirm(`¿Expulsar a ${member.name}?`) && expel.mutate(member.user_id)}
                >
                  Expulsar
                </Button>
              </div>
            )}
          </div>
        ))}
        {expel.isError && <p className="text-sm text-destructive">{expel.error.message}</p>}
      </CardContent>
    </Card>
  )
}

function InvitationsCard({ wid }: { wid: string }) {
  const queryClient = useQueryClient()
  const [maxUses, setMaxUses] = useState('')
  const [created, setCreated] = useState<InvitationCreated | null>(null)
  const invitations = useQuery({
    queryKey: ['invitations', wid],
    queryFn: () => apiGet<Invitation[]>(`/workspaces/${wid}/invitations`),
  })
  const create = useMutation({
    mutationFn: () =>
      apiPost<InvitationCreated>(`/workspaces/${wid}/invitations`, {
        max_uses: maxUses ? Number(maxUses) : null,
      }),
    onSuccess: (invitation) => {
      setCreated(invitation)
      setMaxUses('')
      queryClient.invalidateQueries({ queryKey: ['invitations', wid] })
    },
  })
  const revoke = useMutation({
    mutationFn: (id: string) => apiDelete(`/workspaces/${wid}/invitations/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invitations', wid] }),
  })
  const link = created ? `${window.location.origin}/invite/${created.token}` : ''

  return (
    <Card>
      <CardHeader>
        <CardTitle>Invitaciones</CardTitle>
        <CardDescription>
          Cada link caduca a los 10 días. Mándalo por donde quieras; puedes revocarlo cuando sea.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            create.mutate()
          }}
        >
          <Input
            type="number"
            min={1}
            max={100}
            value={maxUses}
            onChange={(event) => setMaxUses(event.target.value)}
            placeholder="Usos máximos (vacío = sin límite)"
            className="max-w-64"
          />
          <Button type="submit" disabled={create.isPending}>
            Crear link
          </Button>
        </form>
        {create.isError && <p className="text-sm text-destructive">{create.error.message}</p>}

        {created && (
          <div className="flex flex-col gap-2 rounded-lg border bg-muted p-3">
            <p className="text-sm">Copia el link ahora: por seguridad no se vuelve a mostrar.</p>
            <div className="flex gap-2">
              <Input readOnly value={link} onFocus={(event) => event.target.select()} />
              <Button variant="outline" onClick={() => navigator.clipboard.writeText(link)}>
                Copiar
              </Button>
            </div>
          </div>
        )}

        <div className="flex flex-col gap-2">
          {invitations.data?.map((invitation) => (
            <div key={invitation.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <div className="flex items-center gap-2">
                <Badge variant={invitation.status === 'active' ? 'default' : 'secondary'}>
                  {STATUS_LABEL[invitation.status]}
                </Badge>
                <span>
                  Caduca {formatDate(invitation.expires_at)} · {invitation.uses}
                  {invitation.max_uses ? `/${invitation.max_uses}` : ''} usos
                </span>
              </div>
              {invitation.status === 'active' && (
                <Button size="sm" variant="outline" onClick={() => revoke.mutate(invitation.id)}>
                  Revocar
                </Button>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
