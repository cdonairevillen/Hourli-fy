import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api'
import type { Category, Project, Subcategory } from '@/lib/types'

// Catálogo completo del espacio (archivados incluidos) con búsquedas por id.
// Los archivados hacen falta para poner nombre a registros antiguos; los desplegables
// usan solo los activos.
export function useCatalog(wid: string) {
  const projects = useQuery({
    queryKey: ['projects', wid, true],
    queryFn: () => apiGet<Project[]>(`/workspaces/${wid}/projects?include_archived=true`),
  })
  const categories = useQuery({
    queryKey: ['categories', wid, true],
    queryFn: () => apiGet<Category[]>(`/workspaces/${wid}/categories?include_archived=true`),
  })

  const projectById = new Map((projects.data ?? []).map((p) => [p.id, p]))
  const categoryById = new Map((categories.data ?? []).map((c) => [c.id, c]))
  const subcategoryById = new Map<string, Subcategory>(
    (categories.data ?? []).flatMap((c) => c.subcategories.map((s) => [s.id, s] as const)),
  )
  // Para los desplegables: solo labels activas y, dentro, solo sublabels activas.
  const activeCategories = (categories.data ?? [])
    .filter((c) => !c.archived)
    .map((c) => ({ ...c, subcategories: c.subcategories.filter((s) => !s.archived) }))

  // "Acto 1 › Personajes" o solo "Gestión".
  function labelText(categoryId: string, subcategoryId: string | null): string {
    const category = categoryById.get(categoryId)?.name ?? '¿?'
    const sub = subcategoryId ? subcategoryById.get(subcategoryId)?.name : null
    return sub ? `${category} › ${sub}` : category
  }

  return {
    isLoading: projects.isLoading || categories.isLoading,
    projects: projects.data ?? [],
    projectById,
    activeCategories,
    labelText,
  }
}
