import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// Piezas comunes de las listas del catálogo (proyectos, labels y sublabels).

// Nombre que el dueño puede editar en línea: "Renombrar" lo convierte en un formulario.
export function EditableName({
  name,
  canEdit,
  onRename,
  className = '',
}: {
  name: string
  canEdit: boolean
  onRename: (newName: string) => void
  className?: string
}) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(name)

  if (!editing) {
    return (
      <span className={className}>
        {name}
        {canEdit && (
          <Button
            size="sm"
            variant="ghost"
            className="ml-1 h-6 px-2 text-xs text-muted-foreground"
            onClick={() => {
              setValue(name)
              setEditing(true)
            }}
          >
            Renombrar
          </Button>
        )}
      </span>
    )
  }
  return (
    <form
      className="flex flex-1 gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        if (value.trim() && value.trim() !== name) onRename(value.trim())
        setEditing(false)
      }}
    >
      <Input autoFocus value={value} maxLength={80} onChange={(event) => setValue(event.target.value)} />
      <Button type="submit" size="sm">
        Guardar
      </Button>
      <Button type="button" size="sm" variant="ghost" onClick={() => setEditing(false)}>
        Cancelar
      </Button>
    </form>
  )
}

// Botón Archivar / Desarchivar.
export function ArchiveButton({ archived, onToggle }: { archived: boolean; onToggle: () => void }) {
  return (
    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onToggle}>
      {archived ? 'Desarchivar' : 'Archivar'}
    </Button>
  )
}

// Formulario de una línea para crear un elemento por nombre.
export function CreateByName({
  placeholder,
  onCreate,
  disabled,
}: {
  placeholder: string
  onCreate: (name: string) => Promise<unknown>
  disabled?: boolean
}) {
  const [name, setName] = useState('')
  return (
    <form
      className="flex gap-2"
      onSubmit={async (event) => {
        event.preventDefault()
        if (!name.trim()) return
        // Solo se vacía si se creó: si da error (p. ej. nombre repetido) se conserva lo escrito.
        await onCreate(name.trim())
          .then(() => setName(''))
          .catch(() => {})
      }}
    >
      <Input
        value={name}
        maxLength={80}
        placeholder={placeholder}
        onChange={(event) => setName(event.target.value)}
      />
      <Button type="submit" disabled={disabled}>
        Añadir
      </Button>
    </form>
  )
}

// Interruptor "Ver archivados" (solo lo usa el dueño, que es quien puede desarchivar).
export function ShowArchivedToggle({
  checked,
  onChange,
}: {
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-muted-foreground">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      Ver archivados
    </label>
  )
}
