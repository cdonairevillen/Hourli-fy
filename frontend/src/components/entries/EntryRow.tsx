import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { LabelPicker } from '@/components/entries/LabelPicker'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { apiDelete, apiPatch } from '@/lib/api'
import { elapsedSeconds, useNow, useRefreshEntries } from '@/lib/entries'
import { addDays, dayKeyOf, formatClock, formatDuration, formatTime, localToUtcIso } from '@/lib/time'
import type { Category, TimeEntry } from '@/lib/types'

// Una tarea de la hoja: se ve en una línea y "Editar" la convierte en formulario.
export function EntryRow({
  entry,
  categories,
  labelText,
  canEdit,
}: {
  entry: TimeEntry
  categories: Category[]
  labelText: (categoryId: string, subcategoryId: string | null) => string
  canEdit: boolean
}) {
  const [editing, setEditing] = useState(false)
  const refresh = useRefreshEntries()
  const running = entry.end_at === null
  const now = useNow(running)
  const remove = useMutation({
    mutationFn: () => apiDelete(`/entries/${entry.id}`),
    onSuccess: refresh,
  })

  if (editing) {
    return <EntryEditor entry={entry} categories={categories} labelText={labelText} onDone={() => setEditing(false)} />
  }
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2 text-sm">
      <span className="w-24 font-mono text-muted-foreground tabular-nums">
        {formatTime(entry.start_at)}–{entry.end_at ? formatTime(entry.end_at) : '…'}
      </span>
      <div className="flex min-w-48 flex-1 flex-col">
        <span className="font-medium">{entry.title}</span>
        <span className="text-xs text-muted-foreground">
          {labelText(entry.category_id, entry.subcategory_id)}
        </span>
      </div>
      {running ? (
        <Badge variant="destructive" className="font-mono tabular-nums">
          {formatClock(elapsedSeconds(entry, now))}
        </Badge>
      ) : (
        <span className="w-14 text-right font-mono tabular-nums">
          {formatDuration(entry.duration_seconds ?? 0)}
        </span>
      )}
      {canEdit && (
        <div className="flex gap-1">
          <Button size="sm" variant="ghost" className="h-7" onClick={() => setEditing(true)}>
            Editar
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-destructive"
            disabled={remove.isPending}
            onClick={() => confirm(`¿Borrar «${entry.title}»?`) && remove.mutate()}
          >
            Borrar
          </Button>
        </div>
      )}
      {remove.isError && <p className="w-full text-destructive">{remove.error.message}</p>}
    </div>
  )
}

function EntryEditor({
  entry,
  categories,
  labelText,
  onDone,
}: {
  entry: TimeEntry
  categories: Category[]
  labelText: (categoryId: string, subcategoryId: string | null) => string
  onDone: () => void
}) {
  const refresh = useRefreshEntries()
  const running = entry.end_at === null
  const [title, setTitle] = useState(entry.title)
  const [categoryId, setCategoryId] = useState(entry.category_id)
  const [subcategoryId, setSubcategoryId] = useState(entry.subcategory_id)
  const initial = {
    day: dayKeyOf(entry.start_at),
    start: formatTime(entry.start_at),
    end: entry.end_at ? formatTime(entry.end_at) : '',
  }
  const [day, setDay] = useState(initial.day)
  const [start, setStart] = useState(initial.start)
  const [end, setEnd] = useState(initial.end)
  const [category, subcategory] = labelText(entry.category_id, entry.subcategory_id).split(' › ')

  const save = useMutation({
    mutationFn: () => {
      // Solo se manda lo que cambió: así no se pierden los segundos de las horas (aquí se ven
      // como HH:MM) y una label ya archivada que no se toca no da error.
      const body: Record<string, unknown> = {}
      if (title.trim() !== entry.title) body.title = title.trim()
      if (categoryId !== entry.category_id) body.category_id = categoryId
      if (subcategoryId !== entry.subcategory_id) body.subcategory_id = subcategoryId
      const timesChanged = day !== initial.day || start !== initial.start || end !== initial.end
      if (timesChanged) {
        body.start_at = localToUtcIso(day, start)
        // Al cronómetro en marcha no se le pone fin aquí: se para con el botón "Parar".
        if (!running) body.end_at = localToUtcIso(end <= start ? addDays(day, 1) : day, end)
      }
      if (Object.keys(body).length === 0) return Promise.resolve(entry)
      return apiPatch<TimeEntry>(`/entries/${entry.id}`, body)
    },
    onSuccess: () => {
      refresh()
      onDone()
    },
  })

  return (
    <form
      className="flex flex-col gap-2 rounded-lg border bg-muted/40 p-3"
      onSubmit={(event) => {
        event.preventDefault()
        save.mutate()
      }}
    >
      <Input value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
      <LabelPicker
        categories={categories}
        categoryId={categoryId}
        subcategoryId={subcategoryId}
        current={{ category, subcategory: subcategory ?? null }}
        onChange={(newCategory, newSub) => {
          setCategoryId(newCategory)
          setSubcategoryId(newSub)
        }}
      />
      <div className="flex flex-wrap items-center gap-2">
        <Input type="date" value={day} onChange={(e) => setDay(e.target.value)} className="w-40" />
        <Input type="time" value={start} onChange={(e) => setStart(e.target.value)} className="w-28" aria-label="Inicio" />
        {!running && (
          <>
            <span>–</span>
            <Input type="time" value={end} onChange={(e) => setEnd(e.target.value)} className="w-28" aria-label="Fin" />
          </>
        )}
        <Button type="submit" size="sm" disabled={save.isPending || !title.trim() || !categoryId}>
          Guardar
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onDone}>
          Cancelar
        </Button>
      </div>
      {save.isError && <p className="text-sm text-destructive">{save.error.message}</p>}
    </form>
  )
}
