import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { NativeSelect } from '@/components/NativeSelect'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { apiGet, apiUpload } from '@/lib/api'
import { useCatalog } from '@/lib/catalog'
import { formatDuration } from '@/lib/time'
import type { ImportPreview, ImportResult, Member, Workspace } from '@/lib/types'

type LabelChoice = { label: string; sublabel: string }

// Importar un PDF «Informe detallado» de Clockify (solo el dueño). Dos pasos: vista previa
// (no guarda nada) e importar. No se guarda nada entre ellos: al importar se vuelve a mandar
// el mismo archivo junto con lo elegido (a quién va cada persona y en qué label va cada línea).
export function ImportCard({ workspace }: { workspace: Workspace }) {
  const wid = workspace.id
  const queryClient = useQueryClient()
  const catalog = useCatalog(wid)
  const members = useQuery({
    queryKey: ['members', wid],
    queryFn: () => apiGet<Member[]>(`/workspaces/${wid}/members`),
  })
  const [file, setFile] = useState<File | null>(null)
  // 'new' = crear (o usar) un proyecto por nombre; si no, el id de uno existente.
  const [projectId, setProjectId] = useState('new')
  const [projectName, setProjectName] = useState('')
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  // Persona del PDF → id del miembro ('' = fantasma).
  const [people, setPeople] = useState<Record<string, string>>({})
  const [labels, setLabels] = useState<Record<string, LabelChoice>>({})
  const [result, setResult] = useState<ImportResult | null>(null)

  function formWith(extra?: Record<string, string>) {
    const form = new FormData()
    if (file) form.append('file', file)
    for (const [key, value] of Object.entries(extra ?? {})) form.append(key, value)
    return form
  }

  const load = useMutation({
    mutationFn: () => apiUpload<ImportPreview>(`/workspaces/${wid}/imports/preview`, formWith()),
    onSuccess: (data) => {
      setPreview(data)
      setResult(null)
      setPeople(Object.fromEntries(data.people.map((p) => [p.name, p.user_id ?? ''])))
      setLabels(
        Object.fromEntries(
          data.labels.map((l) => [l.project_line, { label: l.label, sublabel: l.sublabel ?? '' }]),
        ),
      )
    },
  })

  const run = useMutation({
    mutationFn: () => {
      const options = {
        project_id: projectId === 'new' ? null : projectId,
        project_name: projectId === 'new' ? projectName.trim() : null,
        people: Object.entries(people).map(([name, userId]) => ({ name, user_id: userId || null })),
        labels: Object.entries(labels).map(([line, choice]) => ({
          project_line: line,
          label: choice.label.trim(),
          sublabel: choice.sublabel.trim() || null,
        })),
      }
      return apiUpload<ImportResult>(
        `/workspaces/${wid}/imports`,
        formWith({ options: JSON.stringify(options) }),
      )
    },
    onSuccess: (data) => {
      setResult(data)
      setPreview(null)
      // Hay miembros (fantasmas), proyectos, labels y horas nuevas.
      for (const key of ['members', 'projects', 'categories', 'report', 'entries']) {
        queryClient.invalidateQueries({ queryKey: [key] })
      }
    },
  })

  const canImport =
    preview !== null &&
    (projectId !== 'new' || projectName.trim() !== '') &&
    Object.values(labels).every((choice) => choice.label.trim() !== '')

  return (
    <Card>
      <CardHeader>
        <CardTitle>Importar de Clockify</CardTitle>
        <CardDescription>
          Sube el PDF «Informe detallado» que exporta Clockify. Todo va a un proyecto; cada
          «proyecto - tarea» de Clockify se convierte en label (el primer trozo) y sublabel (el
          resto). Quien no tenga cuenta queda como «fantasma» y luego puede reclamar sus horas con
          un link (Equipo → Link para reclamar). Reimportar el mismo PDF no duplica nada.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            load.mutate()
          }}
        >
          <Input
            type="file"
            accept="application/pdf"
            className="max-w-80"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null)
              setPreview(null)
            }}
          />
          <Button type="submit" variant="outline" disabled={!file || load.isPending}>
            {load.isPending ? 'Leyendo…' : 'Vista previa'}
          </Button>
        </form>
        {load.isError && <p className="text-sm text-destructive">{load.error.message}</p>}

        {result && (
          <div className="rounded-lg border bg-muted p-3 text-sm">
            <p className="font-medium">
              Importados {result.created_count} registros ({formatDuration(result.imported_seconds)}).
            </p>
            <ul className="list-disc pl-5 text-muted-foreground">
              <li>{result.duplicate_count} ya estaban importados (no se duplican).</li>
              <li>
                {result.shifted_count} se solapaban con otro de la misma persona y se movieron
                justo detrás, con la misma duración.
              </li>
              <li>{result.split_count} duraban más de 24 h y se partieron en trozos.</li>
              {result.empty_count > 0 && <li>{result.empty_count} duraban 0 s y no se guardan.</li>}
              <li>Fantasmas nuevos: {result.ghosts_created.join(', ') || 'ninguno'}.</li>
              <li>
                Labels nuevas: {result.labels_created} · sublabels nuevas: {result.sublabels_created}.
              </li>
            </ul>
          </div>
        )}

        {preview && (
          <div className="flex flex-col gap-4">
            <p className="text-sm">
              {preview.period} · {preview.entry_count} entradas ·{' '}
              <strong>{formatDuration(preview.total_seconds)}</strong> (cuadra con el total del PDF)
            </p>
            {preview.duplicate_count > 0 && (
              <p className="text-sm text-muted-foreground">
                {preview.duplicate_count} entradas ya se importaron antes: se saltarán.
              </p>
            )}

            <div className="flex flex-wrap gap-2">
              <NativeSelect
                aria-label="Proyecto de destino"
                className="max-w-64"
                value={projectId}
                onChange={(event) => setProjectId(event.target.value)}
              >
                <option value="new">Proyecto por nombre (se crea si no existe)…</option>
                {catalog.projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                    {p.archived ? ' (archivado)' : ''}
                  </option>
                ))}
              </NativeSelect>
              {projectId === 'new' && (
                <Input
                  className="max-w-64"
                  value={projectName}
                  maxLength={80}
                  placeholder="Nombre del proyecto"
                  onChange={(event) => setProjectName(event.target.value)}
                />
              )}
            </div>

            <section className="flex flex-col gap-2">
              <h3 className="text-sm font-medium">Personas</h3>
              {preview.people.map((person) => (
                <div key={person.name} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="min-w-48 font-medium">{person.name}</span>
                  <span className="w-28 text-muted-foreground">
                    {person.entry_count} · {formatDuration(person.total_seconds)}
                  </span>
                  <NativeSelect
                    aria-label={`A quién van las horas de ${person.name}`}
                    className="max-w-72"
                    value={people[person.name] ?? ''}
                    onChange={(event) =>
                      setPeople({ ...people, [person.name]: event.target.value })
                    }
                  >
                    <option value="">Fantasma «{person.name}»</option>
                    {members.data?.map((member) => (
                      <option key={member.user_id} value={member.user_id}>
                        {member.name}
                        {member.is_ghost ? ' (fantasma)' : ` · ${member.email}`}
                      </option>
                    ))}
                  </NativeSelect>
                </div>
              ))}
            </section>

            <section className="flex flex-col gap-2">
              <h3 className="text-sm font-medium">Labels</h3>
              {preview.labels.map((label) => {
                const choice = labels[label.project_line] ?? { label: '', sublabel: '' }
                const update = (change: Partial<LabelChoice>) =>
                  setLabels({ ...labels, [label.project_line]: { ...choice, ...change } })
                return (
                  <div key={label.project_line} className="flex flex-col gap-1 text-sm">
                    <span className="text-muted-foreground">
                      {label.project_line || '(sin proyecto)'} · {label.entry_count} ·{' '}
                      {formatDuration(label.total_seconds)}
                      {!label.label_exists && <Badge className="ml-2">label nueva</Badge>}
                      {label.sublabel && !label.sublabel_exists && (
                        <Badge variant="secondary" className="ml-2">
                          sublabel nueva
                        </Badge>
                      )}
                    </span>
                    <div className="flex gap-2">
                      <Input
                        aria-label="Label"
                        value={choice.label}
                        maxLength={80}
                        onChange={(event) => update({ label: event.target.value })}
                      />
                      <Input
                        aria-label="Sublabel"
                        value={choice.sublabel}
                        maxLength={80}
                        placeholder="(sin sublabel)"
                        onChange={(event) => update({ sublabel: event.target.value })}
                      />
                    </div>
                  </div>
                )
              })}
            </section>

            <div className="flex gap-2">
              <Button disabled={!canImport || run.isPending} onClick={() => run.mutate()}>
                {run.isPending ? 'Importando…' : `Importar ${preview.entry_count} entradas`}
              </Button>
              <Button variant="ghost" onClick={() => setPreview(null)}>
                Cancelar
              </Button>
            </div>
            {run.isError && <p className="text-sm text-destructive">{run.error.message}</p>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
