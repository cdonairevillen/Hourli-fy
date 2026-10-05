// Tipos de las respuestas de la API (espejo de backend/app/schemas.py).

export type User = {
  id: string
  name: string
  email: string
  avatar_url: string | null
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
}

export type InvitationStatus = 'active' | 'expired' | 'revoked' | 'exhausted' | 'archived'

export type Invitation = {
  id: string
  created_at: string
  expires_at: string
  max_uses: number | null
  uses: number
  status: InvitationStatus
}

export type InvitationCreated = Invitation & { token: string }

export type InvitationPreview = {
  workspace_name: string
  owner_name: string
  expires_at: string
  status: InvitationStatus
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
