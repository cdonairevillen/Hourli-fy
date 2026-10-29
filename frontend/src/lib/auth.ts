import { useQuery } from '@tanstack/react-query'
import { ApiError, apiGet } from '@/lib/api'
import type { User } from '@/lib/types'

export const GOOGLE_CLIENT_ID: string = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ''
// Sin Client ID el botón de Google ni se pinta: con email + contraseña basta.
export const GOOGLE_ENABLED = GOOGLE_CLIENT_ID !== ''

// Tras cerrar la sesión (o eliminar la cuenta), recarga la app en "/", que sin sesión es el login.
// Recargar borra toda la caché en memoria: la siguiente persona no ve datos de la anterior.
export function goToLogin() {
  window.location.replace('/')
}

// Usuario de la sesión actual, o null si no hay sesión (la API devuelve 401).
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        return await apiGet<User>('/auth/me')
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null
        throw error
      }
    },
    retry: false,
  })
}
