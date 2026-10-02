import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { apiGet } from '@/lib/api'

type Health = { status: string }

function App() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => apiGet<Health>('/health'),
    retry: false,
  })

  let estado = 'comprobando…'
  if (health.isError) estado = `sin conexión (${health.error.message})`
  if (health.data) estado = health.data.status

  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Registro de horas</CardTitle>
          <CardDescription>Fase 0: todo arranca en local.</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p>
            API: <strong>{estado}</strong>
          </p>
          <Button variant="outline" onClick={() => health.refetch()}>
            Reintentar
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}

export default App
