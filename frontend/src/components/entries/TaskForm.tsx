import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { LabelPicker } from '@/components/entries/LabelPicker'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { apiPost } from '@/lib/api'
import { useRefreshEntries } from '@/lib/entries'
import { addDays, localToUtcIso, todayKey } from '@/lib/time'
import type { Category, TimeEntry } from '@/lib/types'

// Nueva tarea en la hoja de un proyecto: nombre libre + label (+ sublabel), y luego
// o se arranca el cronómetro o se apuntan a mano el día y las horas.
export function TaskForm({
  wid,
  projectId,
  categories,
  disabled,
}: {
  wid: string
  projectId: string
  categories: Category[]
  disabled?: boolean
}) {
  const refresh = useRefreshEntries()
  const [title, setTitle] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [subcategoryId, setSubcategoryId] = useState<string | null>(null)
  const [day, setDay] = useState(todayKey)
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')

  const task = {
    project_id: projectId,
    category_id: categoryId,
    subcategory_id: subcategoryId,
    title: title.trim(),
  }
  // La label se conserva tras guardar: lo normal es apuntar varias tareas seguidas de lo mismo.
  const reset = () => {
    setTitle('')
    setStart('')
    setEnd('')
    refresh()
  }
  const startTimer = useMutation({
    mutationFn: () => apiPost<TimeEntry>(`/workspaces/${wid}/timer/start`, task),
    onSuccess: reset,
  })
  const addManual = useMutation({
    mutationFn: () => {
      // Si el fin es anterior al inicio (22:00 → 01:00), el fin es del día siguiente.
      const endDay = end <= start ? addDays(day, 1) : day
      return apiPost<TimeEntry>(`/workspaces/${wid}/entries`, {
        ...task,
        start_at: localToUtcIso(day, start),
        end_at: localToUtcIso(endDay, end),
      })
    },
    onSuccess: reset,
  })

  const ready = !disabled && task.title !== '' && categoryId !== ''
  const error = startTimer.error ?? addManual.error

  return (
    <div className="flex flex-col gap-3 rounded-lg border p-4">
      <Input
        value={title}
        maxLength={200}
        placeholder="¿En qué has trabajado? (p. ej. Animaciones de personajes Pepe y Juan)"
        onChange={(event) => setTitle(event.target.value)}
        disabled={disabled}
      />
      <LabelPicker
        categories={categories}
        categoryId={categoryId}
        subcategoryId={subcategoryId}
        disabled={disabled}
        onChange={(newCategory, newSub) => {
          setCategoryId(newCategory)
          setSubcategoryId(newSub)
        }}
      />
      <div className="flex flex-wrap items-center gap-2">
        <Button disabled={!ready || startTimer.isPending} onClick={() => startTimer.mutate()}>
          ▶ Iniciar cronómetro
        </Button>
        <span className="text-sm text-muted-foreground">o a mano:</span>
        <Input type="date" value={day} onChange={(e) => setDay(e.target.value)} className="w-40" disabled={disabled} />
        <Input type="time" value={start} onChange={(e) => setStart(e.target.value)} className="w-28" aria-label="Inicio" disabled={disabled} />
        <span>–</span>
        <Input type="time" value={end} onChange={(e) => setEnd(e.target.value)} className="w-28" aria-label="Fin" disabled={disabled} />
        <Button
          variant="outline"
          disabled={!ready || !day || !start || !end || addManual.isPending}
          onClick={() => addManual.mutate()}
        >
          Añadir
        </Button>
      </div>
      {error && <p className="text-sm text-destructive">{error.message}</p>}
    </div>
  )
}
