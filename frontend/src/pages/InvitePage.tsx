import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { AuthPanel } from '@/components/auth/AuthPanel'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { apiGet, apiPost } from '@/lib/api'
import { useMe } from '@/lib/auth'
import type { InvitationPreview, Workspace } from '@/lib/types'

const INVALID_REASON: Record<InvitationPreview['status'], string> = {
  active: '',
  expired: 'Este link ha caducado.',
  revoked: 'El dueño ha revocado este link.',
  exhausted: 'Este link ya no admite más usos.',
  archived: 'El espacio está archivado.',
}

// Página de /invite/:token. Se ve sin sesión; si no la hay, el botón de Google aparece aquí
// mismo, así que tras entrar se sigue en la invitación sin redirecciones.
export function InvitePage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const me = useMe()
  const preview = useQuery({
    queryKey: ['invitation', token],
    queryFn: () => apiGet<InvitationPreview>(`/invitations/${token}`),
    retry: false,
  })
  const accept = useMutation({
    mutationFn: () => apiPost<Workspace>(`/invitations/${token}/accept`),
    onSuccess: (workspace) => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      // Invitación a un proyecto: directo a su hoja; al espacio: a su lista de proyectos.
      const projectId = preview.data?.project_id
      navigate(projectId ? `/w/${workspace.id}/p/${projectId}` : `/w/${workspace.id}`)
    },
  })

  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        {preview.isLoading && <CardContent>Cargando…</CardContent>}
        {preview.isError && (
          <CardHeader>
            <CardTitle>Invitación no encontrada</CardTitle>
            <CardDescription>Revisa que el link esté completo.</CardDescription>
          </CardHeader>
        )}
        {preview.data && (
          <>
            <CardHeader>
              <CardTitle>
                {preview.data.project_name
                  ? `Te invitan al proyecto «${preview.data.project_name}»`
                  : `Te invitan a «${preview.data.workspace_name}»`}
              </CardTitle>
              <CardDescription>
                {preview.data.project_name
                  ? `De «${preview.data.workspace_name}» (${preview.data.owner_name}). Verás solo este proyecto.`
                  : `De ${preview.data.owner_name}. Verás todos sus proyectos.`}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-3">
              {preview.data.status !== 'active' ? (
                <p className="text-destructive">{INVALID_REASON[preview.data.status]}</p>
              ) : me.data ? (
                <Button className="w-full" disabled={accept.isPending} onClick={() => accept.mutate()}>
                  Unirme como {me.data.name}
                </Button>
              ) : (
                !me.isLoading && <AuthPanel />
              )}
              {accept.isError && <p className="text-sm text-destructive">{accept.error.message}</p>}
            </CardContent>
          </>
        )}
      </Card>
    </main>
  )
}
