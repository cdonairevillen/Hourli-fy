// Tipos de las respuestas de la API (espejo de backend/app/schemas.py).

export type User = {
  id: string
  name: string
  email: string
  avatar_url: string | null
  // false = cuenta solo de Google (puede ponerse contraseña en Mi cuenta).
  has_password: boolean
  // Su email está en ADMIN_EMAILS: ve el enlace al panel /admin.
  is_admin: boolean
}

export type Workspace = {
  id: string
  name: string
  owner_id: string
  archived: boolean
  is_owner: boolean
  created_at: string
}

export type Member = {
  user_id: string
  name: string
  email: string
  avatar_url: string | null
  is_owner: boolean
  joined_at: string
  // true = ve todos los proyectos del espacio; false = solo los de project_ids.
  all_projects: boolean
  project_ids: string[]
  // Usuario fantasma (horas importadas de alguien sin cuenta): se reclama con un link.
  is_ghost: boolean
}

export type InvitationStatus = 'active' | 'expired' | 'revoked' | 'exhausted' | 'archived'

export type Invitation = {
  id: string
  created_at: string
  expires_at: string
  max_uses: number | null
  uses: number
  status: InvitationStatus
  // null = invitación al espacio entero.
  project_id: string | null
  project_name: string | null
  // Link para reclamar las horas de un fantasma (null = invitación normal).
  claim_user_name: string | null
}

export type InvitationCreated = Invitation & { token: string }

export type InvitationPreview = {
  workspace_name: string
  owner_name: string
  expires_at: string
  status: InvitationStatus
  // Si invita solo a un proyecto.
  project_id: string | null
  project_name: string | null
  // Si es un link para reclamar las horas de un fantasma, su nombre.
  claim_user_name: string | null
}

// Catálogo. En pantalla, categories = "labels" y subcategories = "sublabels".

export type Project = {
  id: string
  name: string
  color: string
  archived: boolean
  created_at: string
}

export type Subcategory = {
  id: string
  category_id: string
  name: string
  archived: boolean
}

export type Category = {
  id: string
  name: string
  archived: boolean
  subcategories: Subcategory[]
}

// Una tarea ya hecha por mí en un proyecto (autocompletar): título y label/sublabel de su último uso.
export type TaskSuggestion = {
  title: string
  category_id: string
  subcategory_id: string | null
  last_used_at: string
}

// Una tarea registrada. end_at null = cronómetro en marcha.
export type TimeEntry = {
  id: string
  workspace_id: string
  project_id: string
  category_id: string
  subcategory_id: string | null
  title: string
  start_at: string
  end_at: string | null
  source: 'manual' | 'timer'
  duration_seconds: number | null
}

// Importar un PDF «Informe detallado» de Clockify (solo el dueño).

export type ImportPerson = {
  // Tal cual sale en el PDF.
  name: string
  entry_count: number
  total_seconds: number
  // Miembro sugerido; null = fantasma nuevo.
  user_id: string | null
  user_name: string | null
  is_ghost: boolean
}

export type ImportLabel = {
  // "Proyecto - tarea" de Clockify.
  project_line: string
  entry_count: number
  total_seconds: number
  label: string
  sublabel: string | null
  // false = se creará al importar.
  label_exists: boolean
  sublabel_exists: boolean
}

export type ImportPreview = {
  period: string
  total_seconds: number
  entry_count: number
  first_day: string
  last_day: string
  // Ya importadas antes en este espacio: se saltan.
  duplicate_count: number
  people: ImportPerson[]
  labels: ImportLabel[]
}

export type ImportResult = {
  project_id: string
  created_count: number
  duplicate_count: number
  shifted_count: number
  split_count: number
  empty_count: number
  imported_seconds: number
  ghosts_created: string[]
  labels_created: number
  sublabels_created: number
}
