import { NativeSelect } from '@/components/NativeSelect'
import type { Category } from '@/lib/types'

// Desplegables de label y sublabel. La sublabel es opcional y solo ofrece las de la label elegida.
// `current` da nombre a una label/sublabel ya archivada que aún lleva un registro antiguo.
export function LabelPicker({
  categories,
  categoryId,
  subcategoryId,
  onChange,
  current,
  disabled,
}: {
  categories: Category[]
  categoryId: string
  subcategoryId: string | null
  onChange: (categoryId: string, subcategoryId: string | null) => void
  current?: { category: string; subcategory: string | null }
  disabled?: boolean
}) {
  const category = categories.find((c) => c.id === categoryId)
  const subcategories = category?.subcategories ?? []
  const archivedSubcategory = subcategoryId && !subcategories.some((s) => s.id === subcategoryId)

  return (
    <div className="flex flex-1 gap-2">
      <NativeSelect
        aria-label="Label"
        value={categoryId}
        disabled={disabled}
        // Al cambiar de label, la sublabel anterior deja de tener sentido.
        onChange={(event) => onChange(event.target.value, null)}
      >
        <option value="" disabled>
          Label…
        </option>
        {categories.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
        {categoryId && !category && (
          <option value={categoryId}>{current?.category ?? 'Label'} (archivada)</option>
        )}
      </NativeSelect>
      <NativeSelect
        aria-label="Sublabel"
        value={subcategoryId ?? ''}
        disabled={disabled || !categoryId || (subcategories.length === 0 && !archivedSubcategory)}
        onChange={(event) => onChange(categoryId, event.target.value || null)}
      >
        <option value="">{subcategories.length ? 'Sin sublabel' : '—'}</option>
        {subcategories.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
        {archivedSubcategory && (
          <option value={subcategoryId}>{current?.subcategory ?? 'Sublabel'} (archivada)</option>
        )}
      </NativeSelect>
    </div>
  )
}
