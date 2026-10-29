import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { apiGet } from '@/lib/api'
import { useCatalog } from '@/lib/catalog'
import {
  addDays,
  dayKeyOf,
  daysBetween,
  formatDay,
  formatDuration,
  fortnightOf,
  todayKey,
  weekOf,
} from '@/lib/time'
import type { TimeEntry, Workspace } from '@/lib/types'

type Mode = 'week' | 'fortnight'

// "Mi hoja": mis horas del espacio en una semana o una quincena, como una hoja de cálculo.
// Filas = proyecto + label; columnas = días. Solo lectura: se edita desde cada proyecto.
export function TimesheetCard({ workspace }: { workspace: Workspace }) {
  const [mode, setMode] = useState<Mode>('fortnight')
  const [anchor, setAnchor] = useState(todayKey)
  const period = mode === 'week' ? weekOf(anchor) : fortnightOf(anchor)
  const days = daysBetween(period.from, period.to)
  const catalog = useCatalog(workspace.id)
  const entries = useQuery({
    queryKey: ['entries', workspace.id, { from: period.from, to: period.to }],
    queryFn: () =>
      apiGet<TimeEntry[]>(`/workspaces/${workspace.id}/entries?from=${period.from}&to=${period.to}`),
  })

  // Suma de segundos por fila (proyecto + label) y día. El cronómetro en marcha aún no suma.
  const rows = new Map<string, { projectId: string; label: string; perDay: Map<string, number> }>()
  for (const entry of entries.data ?? []) {
    if (entry.duration_seconds === null) continue
    const label = catalog.labelText(entry.category_id, null)
    const key = `${entry.project_id}|${entry.category_id}`
    const row = rows.get(key) ?? { projectId: entry.project_id, label, perDay: new Map() }
    const day = dayKeyOf(entry.start_at)
    row.perDay.set(day, (row.perDay.get(day) ?? 0) + entry.duration_seconds)
    rows.set(key, row)
  }
  const sortedRows = [...rows.values()].sort((a, b) => {
    const pa = catalog.projectById.get(a.projectId)?.name ?? ''
    const pb = catalog.projectById.get(b.projectId)?.name ?? ''
    return pa.localeCompare(pb) || a.label.localeCompare(b.label)
  })
  const dayTotal = (day: string) => sortedRows.reduce((sum, r) => sum + (r.perDay.get(day) ?? 0), 0)
  const rowTotal = (perDay: Map<string, number>) => [...perDay.values()].reduce((a, b) => a + b, 0)
  const total = days.reduce((sum, day) => sum + dayTotal(day), 0)
  const cell = (seconds: number) => (seconds ? formatDuration(seconds) : '')

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mi hoja de horas</CardTitle>
        <CardDescription>
          Tus horas en este espacio. Para añadir o corregir tareas, entra en el proyecto.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant={mode === 'fortnight' ? 'default' : 'outline'} onClick={() => setMode('fortnight')}>
            Quincena
          </Button>
          <Button size="sm" variant={mode === 'week' ? 'default' : 'outline'} onClick={() => setMode('week')}>
            Semana
          </Button>
          <div className="ml-auto flex items-center gap-1">
            {/* Saltar desde el primer/último día garantiza caer en el periodo anterior/siguiente. */}
            <Button size="sm" variant="ghost" onClick={() => setAnchor(addDays(period.from, -1))}>
              ‹
            </Button>
            <span className="min-w-52 text-center text-sm font-medium capitalize">{period.label}</span>
            <Button size="sm" variant="ghost" onClick={() => setAnchor(addDays(period.to, 1))}>
              ›
            </Button>
            <Button size="sm" variant="outline" onClick={() => setAnchor(todayKey())}>
              Hoy
            </Button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-muted-foreground">
                <th className="py-2 pr-4 text-left font-medium">Proyecto · label</th>
                {days.map((day) => (
                  <th key={day} className="px-1 py-2 text-center font-normal capitalize">
                    {formatDay(day, { month: undefined })}
                  </th>
                ))}
                <th className="py-2 pl-2 text-right font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((row) => {
                const project = catalog.projectById.get(row.projectId)
                return (
                  <tr key={`${row.projectId}|${row.label}`} className="border-b">
                    <td className="py-2 pr-4">
                      <span className="flex items-center gap-2">
                        <span className="size-2 rounded-full" style={{ background: project?.color }} />
                        {project?.name} · <span className="text-muted-foreground">{row.label}</span>
                      </span>
                    </td>
                    {days.map((day) => (
                      <td key={day} className="px-1 text-center font-mono tabular-nums">
                        {cell(row.perDay.get(day) ?? 0)}
                      </td>
                    ))}
                    <td className="pl-2 text-right font-mono font-medium tabular-nums">
                      {formatDuration(rowTotal(row.perDay))}
                    </td>
                  </tr>
                )
              })}
              <tr className="font-medium">
                <td className="py-2 pr-4">Total</td>
                {days.map((day) => (
                  <td key={day} className="px-1 text-center font-mono tabular-nums">
                    {cell(dayTotal(day))}
                  </td>
                ))}
                <td className="pl-2 text-right font-mono tabular-nums">{formatDuration(total)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        {entries.isSuccess && sortedRows.length === 0 && (
          <p className="text-sm text-muted-foreground">Nada registrado en este periodo.</p>
        )}
      </CardContent>
    </Card>
  )
}
