import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, NavLink, useNavigate, useParams } from 'react-router'
import { CategoriesCard } from '@/components/catalog/CategoriesCard'
import { NativeSelect } from '@/components/NativeSelect'
import { ProjectLinks } from '@/components/entries/ProjectLinks'
import { TimesheetCard } from '@/components/entries/TimesheetCard'
import { ReportPanel } from '@/components/reports/ReportPanel'
import { ProjectsCard } from '@/components/catalog/ProjectsCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from '@/lib/api'
import { useMe } from '@/lib/auth'
import { useCatalog } from '@/lib/catalog'
import type { Invitation, InvitationCreated, Member, Project, Workspace } from '@/lib/types'

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

// Un espacio en pestañas: "Proyectos" (entrada a la hoja de cada uno), "Mi hoja" (mis horas
// por semana/quincena), "Panel" (horas de todo el equipo; solo el dueño), "Catálogo" (proyectos
// y labels) y "Equipo" (ajustes, miembros e invitaciones). Lo del dueño se oculta a los miembros.
export function WorkspacePage({
  tab,
}: {
  tab: 'projects' | 'sheet' | 'panel' | 'catalog' | 'team'
}) {
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
        <TabLink to={`/w/${wid}`}>Proyectos</TabLink>
        <TabLink to={`/w/${wid}/hoja`}>Mi hoja</TabLink>
        {workspace.is_owner && <TabLink to={`/w/${wid}/panel`}>Panel</TabLink>}
        <TabLink to={`/w/${wid}/catalogo`}>Catálogo</TabLink>
        <TabLink to={`/w/${wid}/equipo`}>Equipo</TabLink>
      </nav>

      {tab === 'projects' && <ProjectLinks workspace={workspace} />}
      {tab === 'sheet' && <TimesheetCard workspace={workspace} />}
      {tab === 'panel' &&
        (workspace.is_owner ? (
          <ReportPanel workspace={workspace} />
        ) : (
          <p className="text-sm text-muted-foreground">El panel solo lo ve el dueño del espacio.</p>
        ))}

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
  const [confirmName, setConfirmName] = useState('')
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const remove = useMutation({
    mutationFn: () => apiDelete(`/workspaces/${workspace.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      navigate('/')
    },
  })
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
      <CardContent className="flex flex-col gap-2 border-t pt-4">
        <p className="text-sm font-medium text-destructive">Borrar el espacio</p>
        <p className="text-sm text-muted-foreground">
          Solo si nadie ha registrado horas en él: se borra de verdad, con sus proyectos, labels,
          miembros e invitaciones. Si tiene horas, archívalo.
        </p>
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            remove.mutate()
          }}
        >
          <Input
            className="max-w-64"
            value={confirmName}
            placeholder={`Escribe «${workspace.name}» para confirmar`}
            onChange={(event) => setConfirmName(event.target.value)}
          />
          <Button
            type="submit"
            variant="destructive"
            disabled={confirmName !== workspace.name || remove.isPending}
          >
            Borrar espacio
          </Button>
        </form>
        {remove.isError && <p className="text-sm text-destructive">{remove.error.message}</p>}
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
  const catalog = useCatalog(workspace.id)
  const [editing, setEditing] = useState<string | null>(null)
  const projectNames = (ids: string[]) =>
    ids.map((id) => catalog.projectById.get(id)?.name ?? '¿?').join(', ') || 'ningún proyecto'

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
              <div className="text-xs text-muted-foreground">
                {member.all_projects
                  ? 'Todos los proyectos'
                  : `Solo: ${projectNames(member.project_ids)}`}
              </div>
            </div>
            {workspace.is_owner && member.user_id !== meId && (
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setEditing(editing === member.user_id ? null : member.user_id)}
                >
                  Permisos
                </Button>
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
            {editing === member.user_id && (
              <AccessEditor
                wid={workspace.id}
                member={member}
                projects={catalog.projects}
                onDone={() => setEditing(null)}
              />
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
  // '' = invitación al espacio entero; si no, el id del proyecto.
  const [projectId, setProjectId] = useState('')
  const [created, setCreated] = useState<InvitationCreated | null>(null)
  const catalog = useCatalog(wid)
  const activeProjects = catalog.projects.filter((p) => !p.archived)
  const invitations = useQuery({
    queryKey: ['invitations', wid],
    queryFn: () => apiGet<Invitation[]>(`/workspaces/${wid}/invitations`),
  })
  const create = useMutation({
    mutationFn: () =>
      apiPost<InvitationCreated>(`/workspaces/${wid}/invitations`, {
        max_uses: maxUses ? Number(maxUses) : null,
        project_id: projectId || null,
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
          Al espacio entero (verá todos los proyectos, también los futuros) o a un solo proyecto
          (solo verá ese). Cada link caduca a los 10 días y puedes revocarlo cuando quieras.
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
          <NativeSelect
            aria-label="Alcance"
            className="max-w-64"
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
          >
            <option value="">Todo el espacio</option>
            {activeProjects.map((p) => (
              <option key={p.id} value={p.id}>
                Solo el proyecto {p.name}
              </option>
            ))}
          </NativeSelect>
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
                  {invitation.project_name ? `Proyecto ${invitation.project_name}` : 'Todo el espacio'} ·
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

// Permisos de un miembro: todos los proyectos o una selección. Lo guarda con PUT .../access.
function AccessEditor({
  wid,
  member,
  projects,
  onDone,
}: {
  wid: string
  member: Member
  projects: Project[]
  onDone: () => void
}) {
  const queryClient = useQueryClient()
  const [all, setAll] = useState(member.all_projects)
  const [selected, setSelected] = useState<string[]>(member.project_ids)
  // Activos + los archivados a los que ya tenía acceso (para no perderlos sin querer).
  const options = projects.filter((p) => !p.archived || member.project_ids.includes(p.id))
  const save = useMutation({
    mutationFn: () =>
      apiPut(`/workspaces/${wid}/members/${member.user_id}/access`, {
        all_projects: all,
        project_ids: all ? [] : selected,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', wid] })
      onDone()
    },
  })

  return (
    <div className="flex w-full flex-col gap-2 rounded-lg border bg-muted/40 p-3 text-sm">
      <label className="flex items-center gap-2">
        <input type="checkbox" checked={all} onChange={(e) => setAll(e.target.checked)} />
        Todos los proyectos (también los que se creen después)
      </label>
      {!all && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 pl-6">
          {options.map((p) => (
            <label key={p.id} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selected.includes(p.id)}
                onChange={(e) =>
                  setSelected(
                    e.target.checked ? [...selected, p.id] : selected.filter((id) => id !== p.id),
                  )
                }
              />
              {p.name}
              {p.archived ? ' (archivado)' : ''}
            </label>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Button size="sm" disabled={save.isPending} onClick={() => save.mutate()}>
          Guardar permisos
        </Button>
        <Button size="sm" variant="ghost" onClick={onDone}>
          Cancelar
        </Button>
      </div>
      {save.isError && <p className="text-destructive">{save.error.message}</p>}
    </div>
  )
}
