// Cliente mínimo de la API. Las rutas son relativas (/api/...):
// en dev las reenvía el proxy de Vite y en producción la API sirve también la web (mismo origen).
const API_URL = import.meta.env.VITE_API_URL ?? ''

// Error con el código HTTP y el mensaje (`detail`) que manda FastAPI, para mostrarlo tal cual.
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  // Con FormData (subir archivos) el navegador pone él mismo el Content-Type con su "boundary".
  const isForm = body instanceof FormData
  const response = await fetch(`${API_URL}/api${path}`, {
    method,
    credentials: 'include',
    headers: body === undefined || isForm ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    const detail = typeof data?.detail === 'string' ? data.detail : response.statusText
    throw new ApiError(response.status, detail)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>('GET', path)
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>('POST', path, body ?? {})
}

// POST multipart (archivos): `form` lleva el archivo y los demás campos.
export function apiUpload<T>(path: string, form: FormData): Promise<T> {
  return request<T>('POST', path, form)
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>('PATCH', path, body)
}

export function apiPut<T>(path: string, body: unknown): Promise<T> {
  return request<T>('PUT', path, body)
}

export function apiDelete(path: string): Promise<void> {
  return request<void>('DELETE', path)
}
