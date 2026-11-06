import { useMutation } from '@tanstack/react-query'
import { PictureInPicture2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import { apiPost } from '@/lib/api'
import { elapsedSeconds, useCurrentTimer, useNow, useRefreshEntries } from '@/lib/entries'
import { openFloatingWindow, supportsAlwaysOnTop } from '@/lib/floatingWindow'
import { formatClock } from '@/lib/time'
import type { TimeEntry } from '@/lib/types'

// Cronómetro en marcha, siempre visible en la cabecera (esté en el espacio que esté).
// Además: el tiempo en el título de la pestaña y, con el botón ⧉, una ventanita flotante.
export function TimerBar() {
  const timer = useCurrentTimer()
  const running = timer.data ?? null
  const now = useNow(running !== null)
  const refresh = useRefreshEntries()
  const stop = useMutation({
    mutationFn: () => apiPost<TimeEntry>('/timer/stop'),
    onSettled: refresh,
  })
  const [floating, setFloating] = useState<Window | null>(null)
  const [blocked, setBlocked] = useState(false)
  const clock = running ? formatClock(elapsedSeconds(running, now)) : null

  // Título de la pestaña: "▶ 1:05:12 · Animar a Pepe" mientras corre; al parar, el de siempre.
  useEffect(() => {
    if (!running || !clock) return
    const original = document.title
    document.title = `▶ ${clock} · ${running.title}`
    return () => {
      document.title = original
    }
  }, [running, clock])

  // Si se cierra o recarga la pestaña principal, la ventanita no se queda huérfana.
  useEffect(() => {
    if (!floating) return
    const closeFloating = () => floating.close()
    window.addEventListener('pagehide', closeFloating)
    return () => {
      window.removeEventListener('pagehide', closeFloating)
      closeFloating()
    }
  }, [floating])

  async function openFloating() {
    if (floating) {
      floating.focus()
      return
    }
    const opened = await openFloatingWindow(() => setFloating(null))
    setBlocked(opened === null)
    setFloating(opened)
  }

  return (
    <>
      {running && (
        <div className="flex items-center gap-2 rounded-full border bg-muted px-3 py-1 text-sm">
          <span className="size-2 animate-pulse rounded-full bg-red-500" />
          <Link
            to={`/w/${running.workspace_id}/p/${running.project_id}`}
            className="max-w-48 truncate hover:underline"
            title={running.title}
          >
            {running.title}
          </Link>
          <span className="font-mono tabular-nums">{clock}</span>
          <Button
            size="icon-sm"
            variant="ghost"
            className="size-7"
            onClick={openFloating}
            aria-label="Abrir en una ventanita flotante"
            title={
              supportsAlwaysOnTop()
                ? 'Abrir en una ventanita que queda encima de las demás aplicaciones'
                : 'Abrir en una ventanita aparte'
            }
          >
            <PictureInPicture2 />
          </Button>
          <Button size="sm" variant="destructive" className="h-7" disabled={stop.isPending} onClick={() => stop.mutate()}>
            Parar
          </Button>
        </div>
      )}
      {blocked && !floating && (
        <span className="text-xs text-destructive">El navegador ha bloqueado la ventanita</span>
      )}
      {/* La ventanita sigue abierta al parar: se queda en espera hasta el próximo cronómetro. */}
      {floating &&
        createPortal(
          <FloatingTimer running={running} clock={clock} stopping={stop.isPending} onStop={() => stop.mutate()} />,
          floating.document.body,
        )}
    </>
  )
}

// Contenido de la ventanita: tarea, tiempo grande y botón de parar.
function FloatingTimer({
  running,
  clock,
  stopping,
  onStop,
}: {
  running: TimeEntry | null
  clock: string | null
  stopping: boolean
  onStop: () => void
}) {
  return (
    <div className="flex h-svh flex-col items-center justify-center gap-2 p-3 text-center">
      {running ? (
        <>
          <p className="flex w-full items-center justify-center gap-2 text-sm" title={running.title}>
            <span className="size-2 shrink-0 animate-pulse rounded-full bg-red-500" />
            <span className="truncate">{running.title}</span>
          </p>
          <p className="font-mono text-4xl font-semibold tabular-nums">{clock}</p>
          <Button size="sm" variant="destructive" disabled={stopping} onClick={onStop}>
            Parar
          </Button>
        </>
      ) : (
        <>
          <p className="font-mono text-4xl font-semibold text-muted-foreground tabular-nums">0:00:00</p>
          <p className="text-sm text-muted-foreground">Sin cronómetro en marcha</p>
        </>
      )}
    </div>
  )
}
