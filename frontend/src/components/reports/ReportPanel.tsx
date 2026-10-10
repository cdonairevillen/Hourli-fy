import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { NativeSelect } from '@/components/NativeSelect'
import { DailyHoursChart } from '@/components/reports/DailyHoursChart'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { apiGet } from '@/lib/api'
import { useCatalog } from '@/lib/catalog'
import type { ReportEntriesPage, ReportSummary } from '@/lib/reports'
import { addDays, dayKeyOf, formatDay, formatDuration, formatTime, fortnightOf, todayKey } from '@/lib/time'
import type { Member, Workspace } from '@/lib/types'

const PAGE_SIZE = 50

// Panel del dueño: horas de todo el espacio con filtros. Quincena (o rango), trabajador,
// proyecto, label, sublabel y búsqueda en el nombre de la tarea.
export function ReportPanel({ workspace }: { workspace: Workspace }) {
  const wid = workspace.id
  const catalog = useCatalog(wid)
  const [mode, setMode] = useState<'fortnight' | 'range'>('fortnight')
  const [anchor, setAnchor] = useState(todayKey)
  const fortnight = fortnightOf(anchor)
  const [range, setRange] = useState({ from: fortnight.from, to: fortnight.to })
  const [userId, setUserId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [subcategoryId, setSubcategoryId] = useState('')
  const [search, setSearch] = useState('')
  const q = useDebounced(search.trim(), 400)

  const params = new URLSearchParams()
  if (mode === 'fortnight') {
    params.set('period', `${anchor.slice(0, 7)}-${Number(anchor.slice(8)) <= 15 ? 'A' : 'B'}`)
  } else {
    params.set('from', range.from)
    params.set('to', range.to)
  }
  if (userId) params.set('user_id', userId)
  if (projectId) params.set('project_id', projectId)
  if (categoryId) params.set('category_id', categoryId)
  if (subcategoryId) params.set('subcategory_id', subcategoryId)
  if (q) params.set('q', q)
  const query = params.toString()
  const rangeValid = mode === 'fortnight' || (range.from && range.to && range.from <= range.to)

  const summary = useQuery({
    queryKey: ['report', wid, 'summary', query],
    queryFn: () => apiGet<ReportSummary>(`/workspaces/${wid}/reports/summary?${query}`),
    enabled: !!rangeValid,
  })
  const entries = useInfiniteQuery({
    queryKey: ['report', wid, 'entries', query],
    queryFn: ({ pageParam }) =>
      apiGet<ReportEntriesPage>(
        `/workspaces/${wid}/reports/entries?${query}&limit=${PAGE_SIZE}&offset=${pageParam}`,
      ),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((sum, page) => sum + page.items.length, 0)
      return loaded < last.total ? loaded : undefined
    },
    enabled: !!rangeValid,
  })
  // Miembros activos + quien tenga horas en el periodo (aunque ya no sea miembro).
  const members = useQuery({
    queryKey: ['members', wid],
    queryFn: () => apiGet<Member[]>(`/workspaces/${wid}/members`),
  })
  const people = new Map<string, string>()
  for (const member of members.data ?? []) people.set(member.user_id, member.name)
  for (const user of summary.data?.by_user ?? []) people.set(user.user_id, user.name)

  const selectedCategory = catalog.activeCategories.find((c) => c.id === categoryId)
  const total = summary.data?.total_seconds ?? 0
  const items = entries.data?.pages.flatMap((page) => page.items) ?? []

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Filtros</CardTitle>
          <CardDescription>Solo cuentan tareas terminadas; el cronómetro en marcha aún no suma.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" variant={mode === 'fortnight' ? 'default' : 'outline'} onClick={() => setMode('fortnight')}>
              Quincena
            </Button>
            <Button size="sm" variant={mode === 'range' ? 'default' : 'outline'} onClick={() => setMode('range')}>
              Rango de fechas
            </Button>
            {mode === 'fortnight' ? (
              <div className="ml-auto flex items-center gap-1">
                <Button size="sm" variant="ghost" onClick={() => setAnchor(addDays(fortnight.from, -1))}>
                  ‹
                </Button>
                <span className="min-w-52 text-center text-sm font-medium capitalize">{fortnight.label}</span>
                <Button size="sm" variant="ghost" onClick={() => setAnchor(addDays(fortnight.to, 1))}>
                  ›
                </Button>
                <Button size="sm" variant="outline" onClick={() => setAnchor(todayKey())}>
                  Hoy
                </Button>
              </div>
            ) : (
              <div className="ml-auto flex items-center gap-2">
                <Input type="date" className="w-40" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} />
                <span>–</span>
                <Input type="date" className="w-40" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} />
              </div>
            )}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <NativeSelect aria-label="Trabajador" value={userId} onChange={(e) => setUserId(e.target.value)}>
              <option value="">Todas las personas</option>
              {[...people].map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </NativeSelect>
            <NativeSelect aria-label="Proyecto" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">Todos los proyectos</option>
              {catalog.projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                  {p.archived ? ' (archivado)' : ''}
                </option>
              ))}
            </NativeSelect>
            <NativeSelect
              aria-label="Label"
              value={categoryId}
              onChange={(e) => {
                setCategoryId(e.target.value)
                setSubcategoryId('')
              }}
            >
              <option value="">Todas las labels</option>
              {catalog.activeCategories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </NativeSelect>
            <NativeSelect
              aria-label="Sublabel"
              value={subcategoryId}
              disabled={!selectedCategory?.subcategories.length}
              onChange={(e) => setSubcategoryId(e.target.value)}
            >
              <option value="">Todas las sublabels</option>
              {selectedCategory?.subcategories.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </NativeSelect>
          </div>
          <Input
            value={search}
            maxLength={200}
            placeholder="Buscar en el nombre de la tarea…"
            onChange={(e) => setSearch(e.target.value)}
          />
          {!rangeValid && <p className="text-sm text-destructive">El inicio del rango es posterior al fin.</p>}
          {summary.isError && <p className="text-sm text-destructive">{summary.error.message}</p>}
        </CardContent>
      </Card>

      {summary.data && (
        <>
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-semibold tabular-nums">{formatDuration(total)} h</span>
            <span className="text-muted-foreground">
              en {summary.data.entry_count} tareas · {formatDay(summary.data.from_date)} – {formatDay(summary.data.to_date)}
            </span>
          </div>
          <Card>
            <CardContent className="pt-6">
              <DailyHoursChart
                from={summary.data.from_date}
                to={summary.data.to_date}
                byDay={summary.data.by_day}
                dimmed={summary.isFetching}
              />
            </CardContent>
          </Card>
          <div className="grid gap-4 md:grid-cols-3">
            <TotalsCard
              title="Por persona"
              total={total}
              rows={summary.data.by_user.map((u) => ({ key: u.user_id, name: u.name, seconds: u.total_seconds }))}
            />
            <TotalsCard
              title="Por proyecto"
              total={total}
              rows={summary.data.by_project.map((p) => ({ key: p.project_id, name: p.name, color: p.color, seconds: p.total_seconds }))}
            />
            <TotalsCard
              title="Por label"
              total={total}
              rows={summary.data.by_category.map((c) => ({ key: c.category_id, name: c.name, seconds: c.total_seconds }))}
            />
          </div>
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Tareas</CardTitle>
          <CardDescription>{entries.data?.pages[0]?.total ?? 0} tareas cumplen los filtros.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-3 font-medium">Día</th>
                <th className="py-2 pr-3 font-medium">Persona</th>
                <th className="py-2 pr-3 font-medium">Tarea</th>
                <th className="py-2 pr-3 font-medium">Proyecto · label</th>
                <th className="py-2 text-right font-medium">Horas</th>
              </tr>
            </thead>
            <tbody>
              {items.map((entry) => {
                const project = catalog.projectById.get(entry.project_id)
                return (
                  <tr key={entry.id} className="border-b align-top">
                    <td className="py-2 pr-3 whitespace-nowrap capitalize">
                      {formatDay(dayKeyOf(entry.start_at))}
                      <div className="text-xs text-muted-foreground">
                        {formatTime(entry.start_at)}–{entry.end_at ? formatTime(entry.end_at) : ''}
                      </div>
                    </td>
                    <td className="py-2 pr-3">{entry.user_name}</td>
                    <td className="py-2 pr-3">{entry.title}</td>
                    <td className="py-2 pr-3">
                      <span className="flex items-center gap-2">
                        <span className="size-2 shrink-0 rounded-full" style={{ background: project?.color }} />
                        {project?.name}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {catalog.labelText(entry.category_id, entry.subcategory_id)}
                      </span>
                    </td>
                    <td className="py-2 text-right font-mono tabular-nums">
                      {formatDuration(entry.duration_seconds ?? 0)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {entries.hasNextPage && (
            <Button variant="ghost" className="mt-2" disabled={entries.isFetchingNextPage} onClick={() => entries.fetchNextPage()}>
              Cargar más
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function TotalsCard({
  title,
  rows,
  total,
}: {
  title: string
  rows: { key: string; name: string; color?: string; seconds: number }[]
  total: number
}) {
  const max = Math.max(...rows.map((row) => row.seconds), 0)
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-1 text-sm">
        {rows.length === 0 && <p className="text-muted-foreground">Sin horas.</p>}
        {rows.map((row) => (
          <div key={row.key} className="flex flex-col gap-1 py-1">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate">{row.name}</span>
              <span className="shrink-0 font-mono tabular-nums">
                {formatDuration(row.seconds)}
                <span className="ml-2 text-xs text-muted-foreground">
                  {total ? Math.round((row.seconds / total) * 100) : 0}%
                </span>
              </span>
            </div>
            {/* Barra fina proporcional al mayor de la lista. Proyectos: su color (identidad);
                personas y labels: el color único de serie. El texto nunca va en color. */}
            <div className="h-2">
              <div
                className="h-full rounded-r-[4px]"
                style={{
                  width: `${max ? (row.seconds / max) * 100 : 0}%`,
                  background: row.color ?? 'var(--series-1)',
                }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// El valor tras `ms` sin cambios: la búsqueda no lanza una petición por cada tecla.
function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(id)
  }, [value, ms])
  return debounced
}
