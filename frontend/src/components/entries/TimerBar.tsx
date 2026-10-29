import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import { apiPost } from '@/lib/api'
import { elapsedSeconds, useCurrentTimer, useNow, useRefreshEntries } from '@/lib/entries'
import { formatClock } from '@/lib/time'
import type { TimeEntry } from '@/lib/types'

// Cronómetro en marcha, siempre visible en la cabecera (esté en el espacio que esté).
export function TimerBar() {
  const timer = useCurrentTimer()
  const running = timer.data ?? null
  const now = useNow(running !== null)
  const refresh = useRefreshEntries()
  const stop = useMutation({
    mutationFn: () => apiPost<TimeEntry>('/timer/stop'),
    onSettled: refresh,
  })

  if (!running) return null
  return (
    <div className="flex items-center gap-2 rounded-full border bg-muted px-3 py-1 text-sm">
      <span className="size-2 animate-pulse rounded-full bg-red-500" />
      <Link
        to={`/w/${running.workspace_id}/p/${running.project_id}`}
        className="max-w-48 truncate hover:underline"
        title={running.title}
      >
        {running.title}
      </Link>
      <span className="font-mono tabular-nums">{formatClock(elapsedSeconds(running, now))}</span>
      <Button size="sm" variant="destructive" className="h-7" disabled={stop.isPending} onClick={() => stop.mutate()}>
        Parar
      </Button>
    </div>
  )
}
