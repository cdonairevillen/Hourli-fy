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
import type { Category, Subcategory, Workspace } from '@/lib/types'

type CatalogChange = { name?: string; archived?: boolean }

// Labels (tipologías) del espacio con sus sublabels. Las crea el dueño y todos las usan al
// registrar tareas en cualquier proyecto: "Acto 1 › Personajes 3D", "Gestión"...
export function CategoriesCard({ workspace }: { workspace: Workspace }) {
  const queryClient = useQueryClient()
  const [showArchived, setShowArchived] = useState(false)
  const canEdit = workspace.is_owner && !workspace.archived
  const base = `/workspaces/${workspace.id}/categories`

  const categories = useQuery({
    queryKey: ['categories', workspace.id, showArchived],
    queryFn: () => apiGet<Category[]>(`${base}?include_archived=${showArchived}`),
  })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['categories', workspace.id] })
  const createCategory = useMutation({
    mutationFn: (name: string) => apiPost<Category>(base, { name }),
    onSuccess: refresh,
  })
  const updateCategory = useMutation({
    mutationFn: ({ id, ...body }: CatalogChange & { id: string }) =>
      apiPatch<Category>(`${base}/${id}`, body),
    onSuccess: refresh,
  })
  const createSubcategory = useMutation({
    mutationFn: ({ categoryId, name }: { categoryId: string; name: string }) =>
      apiPost<Subcategory>(`${base}/${categoryId}/subcategories`, { name }),
    onSuccess: refresh,
  })
  const updateSubcategory = useMutation({
    mutationFn: ({ sub, ...body }: CatalogChange & { sub: Subcategory }) =>
      apiPatch<Subcategory>(`${base}/${sub.category_id}/subcategories/${sub.id}`, body),
    onSuccess: refresh,
  })
  const error =
    createCategory.error ?? updateCategory.error ?? createSubcategory.error ?? updateSubcategory.error

  return (
    <Card>
      <CardHeader>
        <CardTitle>Labels</CardTitle>
        <CardDescription>
          Las partes del trabajo que se eligen al registrar una tarea. Cada label puede tener
          sublabels para concretar (opcionales).
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {canEdit && (
          <CreateByName
            placeholder="Nueva label (p. ej. Acto 1, Gestión…)"
            onCreate={createCategory.mutateAsync}
          />
        )}
        {workspace.is_owner && <ShowArchivedToggle checked={showArchived} onChange={setShowArchived} />}
        {error && <p className="text-sm text-destructive">{error.message}</p>}

        {categories.isSuccess && categories.data.length === 0 && (
          <p className="text-sm text-muted-foreground">Aún no hay labels.</p>
        )}
        {categories.data?.map((category) => (
          <div key={category.id} className="flex flex-col gap-2 rounded-lg border p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-1 items-center gap-2">
                <EditableName
                  name={category.name}
                  canEdit={canEdit}
                  className={category.archived ? 'text-muted-foreground line-through' : 'font-medium'}
                  onRename={(name) => updateCategory.mutate({ id: category.id, name })}
                />
                {category.archived && <Badge variant="secondary">Archivada</Badge>}
              </div>
              {canEdit && (
                <ArchiveButton
                  archived={category.archived}
                  onToggle={() =>
                    updateCategory.mutate({ id: category.id, archived: !category.archived })
                  }
                />
              )}
            </div>

            <div className="ml-4 flex flex-col gap-1 border-l pl-3">
              {category.subcategories.map((sub) => (
                <div key={sub.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <div className="flex flex-1 items-center gap-2">
                    <EditableName
                      name={sub.name}
                      canEdit={canEdit}
                      className={sub.archived ? 'text-muted-foreground line-through' : ''}
                      onRename={(name) => updateSubcategory.mutate({ sub, name })}
                    />
                    {sub.archived && <Badge variant="secondary">Archivada</Badge>}
                  </div>
                  {canEdit && (
                    <ArchiveButton
                      archived={sub.archived}
                      onToggle={() => updateSubcategory.mutate({ sub, archived: !sub.archived })}
                    />
                  )}
                </div>
              ))}
              {canEdit && (
                <CreateByName
                  placeholder={`Nueva sublabel de ${category.name}`}
                  onCreate={(name) => createSubcategory.mutateAsync({ categoryId: category.id, name })}
                />
              )}
              {!canEdit && category.subcategories.length === 0 && (
                <p className="text-sm text-muted-foreground">Sin sublabels.</p>
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
