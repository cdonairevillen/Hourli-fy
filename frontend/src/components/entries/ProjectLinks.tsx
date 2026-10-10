import { Link } from 'react-router'
import { useCatalog } from '@/lib/catalog'
import type { Workspace } from '@/lib/types'

// Pestaña "Proyectos": la entrada del día a día. Cada proyecto abre su hoja de tareas.
export function ProjectLinks({ workspace }: { workspace: Workspace }) {
  const catalog = useCatalog(workspace.id)
  const active = catalog.projects.filter((p) => !p.archived)

  if (catalog.isLoading) return <p className="text-muted-foreground">Cargando…</p>
  if (active.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {workspace.is_owner
          ? 'Aún no hay proyectos. Créalos en la pestaña Catálogo.'
          : 'Aún no hay proyectos. Los crea el dueño del espacio.'}
      </p>
    )
  }
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {active.map((project) => (
        <Link
          key={project.id}
          to={`/w/${workspace.id}/p/${project.id}`}
          className="flex items-center gap-3 rounded-lg border p-4 hover:bg-accent"
        >
          <span className="size-3 shrink-0 rounded-full" style={{ background: project.color }} />
          <span className="font-medium">{project.name}</span>
        </Link>
      ))}
    </div>
  )
}
