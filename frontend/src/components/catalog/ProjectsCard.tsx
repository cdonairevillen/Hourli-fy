import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  ArchiveButton,
  CreateByName,
  EditableName,
  ShowArchivedToggle,
} from '@/components/catalog/ItemActions'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { apiGet, apiPatch, apiPost } from '@/lib/api'
import type { Project, Workspace } from '@/lib/types'

// Paleta para distinguir proyectos (la API acepta cualquier #RRGGBB; esto solo facilita elegir).
const PALETTE = ['#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#14b8a6', '#64748b']

// Proyectos del espacio. Cada uno será la puerta a su hoja de tareas (fase 3).
export function ProjectsCard({ workspace }: { workspace: Workspace }) {
  const queryClient = useQueryClient()
  const [showArchived, setShowArchived] = useState(false)
  const [color, setColor] = useState(PALETTE[0])
  const canEdit = workspace.is_owner && !workspace.archived
  const base = `/workspaces/${workspace.id}/projects`

  const projects = useQuery({
    queryKey: ['projects', workspace.id, showArchived],
    queryFn: () => apiGet<Project[]>(`${base}?include_archived=${showArchived}`),
  })
  // Prefijo ['projects', wid]: invalida la lista con y sin archivados.
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['projects', workspace.id] })
  const create = useMutation({
    mutationFn: (name: string) => apiPost<Project>(base, { name, color }),
    onSuccess: refresh,
  })
  const update = useMutation({
    mutationFn: ({ id, ...body }: Partial<Project> & { id: string }) =>
      apiPatch<Project>(`${base}/${id}`, body),
    onSuccess: refresh,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Proyectos</CardTitle>
        <CardDescription>
          Cada proyecto tendrá su hoja de tareas. Archivar uno lo oculta, pero no borra sus horas.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {canEdit && (
          <div className="flex flex-col gap-2">
            <CreateByName placeholder="Nombre del proyecto" onCreate={create.mutateAsync} />
            <ColorPicker value={color} onChange={setColor} />
          </div>
        )}
        {workspace.is_owner && <ShowArchivedToggle checked={showArchived} onChange={setShowArchived} />}
        {(create.isError || update.isError) && (
          <p className="text-sm text-destructive">{(create.error ?? update.error)?.message}</p>
        )}

        <div className="flex flex-col gap-2">
          {projects.isSuccess && projects.data.length === 0 && (
            <p className="text-sm text-muted-foreground">Aún no hay proyectos.</p>
          )}
          {projects.data?.map((project) => (
            <div key={project.id} className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-1 items-center gap-2">
                <span className="size-3 shrink-0 rounded-full" style={{ background: project.color }} />
                <EditableName
                  name={project.name}
                  canEdit={canEdit}
                  className={project.archived ? 'text-muted-foreground line-through' : 'font-medium'}
                  onRename={(name) => update.mutate({ id: project.id, name })}
                />
                {project.archived && <Badge variant="secondary">Archivado</Badge>}
              </div>
              {canEdit && (
                <div className="flex items-center gap-2">
                  <ColorPicker
                    value={project.color}
                    onChange={(newColor) => update.mutate({ id: project.id, color: newColor })}
                    small
                  />
                  <ArchiveButton
                    archived={project.archived}
                    onToggle={() => update.mutate({ id: project.id, archived: !project.archived })}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function ColorPicker({
  value,
  onChange,
  small = false,
}: {
  value: string
  onChange: (color: string) => void
  small?: boolean
}) {
  return (
    <div className="flex gap-1" role="radiogroup" aria-label="Color">
      {PALETTE.map((color) => (
        <button
          key={color}
          type="button"
          role="radio"
          aria-checked={value.toLowerCase() === color}
          aria-label={color}
          onClick={() => onChange(color)}
          className={`rounded-full ${small ? 'size-4' : 'size-6'} ${value.toLowerCase() === color ? 'ring-2 ring-ring ring-offset-2' : ''}`}
          style={{ background: color }}
        />
      ))}
    </div>
  )
}
