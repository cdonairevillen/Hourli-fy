import { GoogleLoginButton } from '@/components/GoogleLoginButton'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function LoginPage() {
  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Hourli-fy</CardTitle>
          <CardDescription>Registro de horas por proyecto. Entra con tu cuenta de Google.</CardDescription>
        </CardHeader>
        <CardContent>
          <GoogleLoginButton />
        </CardContent>
      </Card>
    </main>
  )
}
