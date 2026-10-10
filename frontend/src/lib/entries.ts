import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { apiGet } from '@/lib/api'
import type { TimeEntry } from '@/lib/types'

// Cronómetro en marcha (uno por persona, en cualquier espacio) o null.
export function useCurrentTimer() {
  return useQuery({
    queryKey: ['timer'],
    queryFn: () => apiGet<TimeEntry | null>('/timer/current'),
    // Por si se arranca o para desde otra pestaña u otro equipo.
    refetchInterval: 60_000,
  })
}

// Tras crear, editar, borrar, arrancar o parar: refresca registros y cronómetro.
export function useRefreshEntries() {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: ['entries'] })
    queryClient.invalidateQueries({ queryKey: ['timer'] })
  }
}

// La hora actual, actualizada cada segundo mientras `active` (para pintar el cronómetro).
// El tiempo transcurrido se calcula siempre como ahora - inicio: el servidor es quien manda.
export function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!active) return
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [active])
  return now
}

export function elapsedSeconds(entry: TimeEntry, now: number): number {
  if (entry.duration_seconds !== null) return entry.duration_seconds
  return (now - new Date(entry.start_at).getTime()) / 1000
}
