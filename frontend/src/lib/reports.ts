// Tipos del panel del dueño (espejo de ReportSummary / ReportEntriesPage en backend/app/schemas.py).
import type { TimeEntry } from '@/lib/types'

export type ReportSummary = {
  from_date: string
  to_date: string
  total_seconds: number
  entry_count: number
  by_user: { user_id: string; name: string; total_seconds: number }[]
  by_project: { project_id: string; name: string; color: string; total_seconds: number }[]
  by_category: { category_id: string; name: string; total_seconds: number }[]
  // Día en hora de España (AAAA-MM-DD); solo aparecen los días con horas.
  by_day: { day: string; total_seconds: number }[]
}

export type ReportEntry = TimeEntry & { user_id: string; user_name: string }

export type ReportEntriesPage = {
  total: number
  items: ReportEntry[]
}
