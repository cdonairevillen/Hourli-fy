import { Link } from 'react-router'
import { AuthPanel } from '@/components/auth/AuthPanel'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function LoginPage() {
  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Hourli-fy</CardTitle>
          <CardDescription>Registro de horas por proyecto. Entra o crea tu cuenta.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          <AuthPanel />
          <Link to="/privacidad" className="text-xs text-muted-foreground hover:underline">
            Privacidad
          </Link>
        </CardContent>
      </Card>
    </main>
  )
}
