// Fechas y horas. La API guarda y devuelve instantes en UTC; aquí todo se muestra y se escribe
// en hora de España, aunque el navegador esté en otra zona horaria.
// Un "día" se representa como texto 'AAAA-MM-DD' (dayKey): es fácil de comparar y de mandar a la API.

export const TIME_ZONE = 'Europe/Madrid'

const dayKeyFormat = new Intl.DateTimeFormat('en-CA', {
  timeZone: TIME_ZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})
const timeFormat = new Intl.DateTimeFormat('es-ES', {
  timeZone: TIME_ZONE,
  hour: '2-digit',
  minute: '2-digit',
})
const partsFormat = new Intl.DateTimeFormat('en-US', {
  timeZone: TIME_ZONE,
  hourCycle: 'h23',
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: 'numeric',
  minute: 'numeric',
  second: 'numeric',
})

// Día en España de un instante: '2026-10-05T23:30:00Z' → '2026-10-06'.
export function dayKeyOf(value: string | Date): string {
  return dayKeyFormat.format(new Date(value))
}

export function todayKey(): string {
  return dayKeyOf(new Date())
}

// Hora en España: '08:30'.
export function formatTime(value: string | Date): string {
  return timeFormat.format(new Date(value))
}

// '2026-10-05' → 'lun 5 oct'.
export function formatDay(key: string, options?: Intl.DateTimeFormatOptions): string {
  return keyToUtcNoon(key).toLocaleDateString('es-ES', {
    timeZone: 'UTC',
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    ...options,
  })
}

// Segundos → '2:05' (horas:minutos), como en una hoja de horas.
export function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`
}

// Segundos → '2:05:09' para el cronómetro en marcha.
export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  const hh = Math.floor(s / 3600)
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

// Diferencia (ms) entre la hora de España y UTC en ese instante: +2 h en verano, +1 h en invierno.
function offsetAt(utcMs: number): number {
  const parts = Object.fromEntries(
    partsFormat.formatToParts(new Date(utcMs)).map((part) => [part.type, part.value]),
  )
  const asUtc = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour),
    Number(parts.minute),
    Number(parts.second),
  )
  return asUtc - (utcMs - (utcMs % 1000))
}

// Día + hora escritos en España → instante en UTC (ISO) para la API.
// Se calcula dos veces por si el cambio de hora cae justo entre la suposición y el resultado.
export function localToUtcIso(key: string, hhmm: string): string {
  const [year, month, day] = key.split('-').map(Number)
  const [hour, minute] = hhmm.split(':').map(Number)
  const wallClock = Date.UTC(year, month - 1, day, hour, minute)
  let utc = wallClock - offsetAt(wallClock)
  utc = wallClock - offsetAt(utc)
  return new Date(utc).toISOString()
}

function keyToUtcNoon(key: string): Date {
  const [year, month, day] = key.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day, 12))
}

export function addDays(key: string, days: number): string {
  const date = keyToUtcNoon(key)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function daysBetween(from: string, to: string): string[] {
  const days: string[] = []
  for (let key = from; key <= to; key = addDays(key, 1)) days.push(key)
  return days
}

export type Period = { from: string; to: string; label: string }

// Semana de lunes a domingo que contiene ese día.
export function weekOf(key: string): Period {
  const weekday = (keyToUtcNoon(key).getUTCDay() + 6) % 7 // 0 = lunes
  const from = addDays(key, -weekday)
  const to = addDays(from, 6)
  return { from, to, label: `Semana del ${formatDay(from, { weekday: undefined })}` }
}

// Quincena A (días 1–15) o B (16–fin de mes) que contiene ese día.
export function fortnightOf(key: string): Period {
  const [year, month, day] = key.split('-').map(Number)
  const prefix = key.slice(0, 7)
  const monthName = keyToUtcNoon(key).toLocaleDateString('es-ES', {
    timeZone: 'UTC',
    month: 'long',
    year: 'numeric',
  })
  if (day <= 15) return { from: `${prefix}-01`, to: `${prefix}-15`, label: `Quincena A · ${monthName}` }
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate()
  return { from: `${prefix}-16`, to: `${prefix}-${lastDay}`, label: `Quincena B · ${monthName}` }
}
