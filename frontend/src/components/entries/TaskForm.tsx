import { useMutation, useQuery } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { LabelPicker } from '@/components/entries/LabelPicker'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { apiGet, apiPost } from '@/lib/api'
import { useRefreshEntries } from '@/lib/entries'
import { addDays, localToUtcIso, todayKey } from '@/lib/time'
import type { Category, TaskSuggestion, TimeEntry } from '@/lib/types'

// Nueva tarea en la hoja de un proyecto: nombre libre + label (+ sublabel), y luego
// o se arranca el cronómetro o se apuntan a mano el día y las horas.
// El nombre se autocompleta con mis tareas anteriores en el proyecto; al elegir una se ponen
// también su label y sublabel.
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
  const suggestionsId = useId()
  // Bajo la clave ['entries', …]: tras guardar una tarea, useRefreshEntries la recarga también.
  const suggestions = useQuery({
    queryKey: ['entries', wid, 'suggestions', projectId],
    queryFn: () =>
      apiGet<TaskSuggestion[]>(`/workspaces/${wid}/entries/suggestions?project_id=${projectId}`),
    enabled: !disabled,
  })

  // Al escribir o elegir exactamente una tarea anterior, se ponen su label y sublabel (si siguen
  // activas; si la label se archivó, solo se aprovecha el nombre).
  function changeTitle(value: string) {
    setTitle(value)
    const match = suggestions.data?.find((s) => s.title === value)
    const category = match && categories.find((c) => c.id === match.category_id)
    if (!match || !category) return
    setCategoryId(category.id)
    setSubcategoryId(category.subcategories.some((s) => s.id === match.subcategory_id) ? match.subcategory_id : null)
  }

  function labelOf(suggestion: TaskSuggestion): string {
    const category = categories.find((c) => c.id === suggestion.category_id)
    const subcategory = category?.subcategories.find((s) => s.id === suggestion.subcategory_id)
    if (!category) return ''
    return subcategory ? `${category.name} › ${subcategory.name}` : category.name
  }

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
        onChange={(event) => changeTitle(event.target.value)}
        disabled={disabled}
        list={suggestionsId}
        // Sin el autocompletado propio del navegador: se solaparía con el nuestro.
        autoComplete="off"
      />
      {/* datalist: el navegador muestra y filtra la lista mientras se escribe. */}
      <datalist id={suggestionsId}>
        {suggestions.data?.map((s) => (
          <option key={s.title} value={s.title} label={labelOf(s)} />
        ))}
      </datalist>
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
