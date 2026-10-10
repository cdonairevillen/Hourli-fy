import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { EntryRow } from '@/components/entries/EntryRow'
import { TaskForm } from '@/components/entries/TaskForm'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { apiGet, apiPatch } from '@/lib/api'
import { useCatalog } from '@/lib/catalog'
import { addDays, dayKeyOf, formatDay, formatDuration, todayKey } from '@/lib/time'
import type { TimeEntry, Workspace } from '@/lib/types'

const PAGE_DAYS = 30

// Hoja de un proyecto: aquí se registran las tareas, y todas quedan ligadas a este proyecto.
// Cada persona ve sus propias tareas; los totales de todo el equipo son del panel (fase 4).
export function ProjectSheetPage() {
  const { wid = '', pid = '' } = useParams()
  const [days, setDays] = useState(PAGE_DAYS)
  const from = addDays(todayKey(), -days + 1)
  const workspaces = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => apiGet<Workspace[]>('/workspaces'),
  })
  const workspace = workspaces.data?.find((w) => w.id === wid)
  const catalog = useCatalog(wid)
  const project = catalog.projectById.get(pid)
  const queryClient = useQueryClient()
  // El dueño puede archivar (o desarchivar) el proyecto desde su propia hoja.
  const toggleArchived = useMutation({
    mutationFn: (archived: boolean) =>
      apiPatch(`/workspaces/${wid}/projects/${pid}`, { archived }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects', wid] }),
  })
  const entries = useQuery({
    queryKey: ['entries', wid, { project: pid, from }],
    queryFn: () =>
      apiGet<TimeEntry[]>(`/workspaces/${wid}/entries?project_id=${pid}&from=${from}`),
    enabled: !!workspace,
  })

  if (workspaces.isLoading || catalog.isLoading) return <p className="text-muted-foreground">Cargando…</p>
  if (!workspace || !project) {
    return (
      <p>
        Proyecto no encontrado. <Link to={`/w/${wid}`} className="underline">Volver</Link>
      </p>
    )
  }

  const canWrite = !workspace.archived && !project.archived
  // Agrupadas por día (de España), del más reciente al más antiguo; la API ya las da ordenadas.
  const byDay = new Map<string, TimeEntry[]>()
  for (const entry of entries.data ?? []) {
    const key = dayKeyOf(entry.start_at)
    byDay.set(key, [...(byDay.get(key) ?? []), entry])
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        <Link to="/" className="text-muted-foreground hover:underline">
          Espacios /
        </Link>
        <Link to={`/w/${wid}`} className="text-muted-foreground hover:underline">
          {workspace.name} /
        </Link>
        <span className="size-3 rounded-full" style={{ background: project.color }} />
        <h1 className="text-xl font-semibold">{project.name}</h1>
        {project.archived && <Badge variant="secondary">Archivado</Badge>}
        {workspace.is_owner && !workspace.archived && (
          <Button
            size="sm"
            variant="outline"
            className="ml-auto"
            disabled={toggleArchived.isPending}
            onClick={() =>
              (project.archived || confirm(`¿Archivar «${project.name}»? Sus horas se conservan.`)) &&
              toggleArchived.mutate(!project.archived)
            }
          >
            {project.archived ? 'Desarchivar proyecto' : 'Archivar proyecto'}
          </Button>
        )}
      </div>

      {canWrite ? (
        <TaskForm wid={wid} projectId={pid} categories={catalog.activeCategories} />
      ) : (
        <p className="text-sm text-muted-foreground">
          {workspace.archived ? 'El espacio' : 'El proyecto'} está archivado: no se pueden
          añadir tareas.
        </p>
      )}
      {canWrite && catalog.activeCategories.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Aún no hay labels en este espacio. El dueño las crea en la pestaña Catálogo.
        </p>
      )}

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">Mis tareas en este proyecto</h2>
        {entries.isError && <p className="text-destructive">{entries.error.message}</p>}
        {entries.isSuccess && entries.data.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No has registrado nada en los últimos {days} días.
          </p>
        )}
        {[...byDay].map(([day, dayEntries]) => (
          <div key={day}>
            <div className="flex justify-between border-b pb-1 text-sm font-medium">
              <span className="capitalize">{formatDay(day)}</span>
              <span className="font-mono tabular-nums">
                {formatDuration(dayEntries.reduce((sum, e) => sum + (e.duration_seconds ?? 0), 0))}
              </span>
            </div>
            <div className="divide-y">
              {dayEntries.map((entry) => (
                <EntryRow
                  key={entry.id}
                  entry={entry}
                  categories={catalog.activeCategories}
                  labelText={catalog.labelText}
                  canEdit={!workspace.archived}
                />
              ))}
            </div>
          </div>
        ))}
        {entries.isSuccess && (
          <Button variant="ghost" className="self-start" onClick={() => setDays(days + PAGE_DAYS)}>
            Ver {PAGE_DAYS} días más
          </Button>
        )}
      </section>
    </div>
  )
}
