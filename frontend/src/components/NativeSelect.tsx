import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

// Desplegable nativo con el mismo aspecto que <Input>. Nativo a propósito: funciona con
// teclado y en móvil sin más, y para elegir label/sublabel no hace falta nada más elaborado.
export function NativeSelect({ className, ...props }: ComponentProps<'select'>) {
  return (
    <select
      className={cn(
        'h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
}
