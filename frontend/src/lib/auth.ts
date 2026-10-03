import { useQuery } from '@tanstack/react-query'
import { ApiError, apiGet } from '@/lib/api'
import type { User } from '@/lib/types'

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
