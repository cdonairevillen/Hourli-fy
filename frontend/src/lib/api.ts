// Cliente mínimo de la API. Las rutas son relativas (/api/...):
// en dev las reenvía el proxy de Vite y en producción irán a la URL del backend.
const API_URL = import.meta.env.VITE_API_URL ?? ''

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}/api${path}`, { credentials: 'include' })
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}
