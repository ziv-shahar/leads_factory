/**
 * TypeScript types matching the Supabase database schema
 * Generated from models.py and SQL migrations
 */

// ============================================================================
// Core Entity Types
// ============================================================================

export interface Entity {
  id: number
  canonical_name: string
  normalized_name: string
  domain: string | null
  entity_type: string | null
  entity_metadata: EntityMetadata
  last_enriched_at: string | null
  created_at: string
}

export interface EntityMetadata {
  // Company metadata
  website_url?: string
  linkedin_url?: string
  hq_city?: string
  hq_state?: string
  industry?: string
  employee_count?: number

  // Government agency metadata
  agency_code?: string
  jurisdiction?: string
  parent_agency?: string
  gov_domain?: string

  // Contractor metadata
  sam_gov_uei?: string
  duns_number?: string
  cage_code?: string
  naics_codes?: string[]

  // Additional flexible fields
  [key: string]: any
}

// ============================================================================
// Event Types
// ============================================================================

export interface Event {
  id: string  // UUID
  entity_id: number
  source: string
  event_type: string
  event_time: string | null
  ingest_time: string
  strict: EventStrict
  dynamic_signals: DynamicSignal[]
  extraction_confidence: number
  raw_ref: string
}

export interface EventStrict {
  summary?: string
  key_facts?: string[] | {
    // Direct opportunity properties
    aboa_sf_min?: number
    aboa_sf_max?: number
    amount?: string

    // Nested properties under "other" for government opportunities
    other?: {
      solicitation_number?: string
      response_deadline?: string
      opportunity_status?: string
      notice_type?: string
      delineated_area?: string
      lease_term_years?: number
      firm_term_years?: number
      parking_spaces?: number
      facility_security_level?: string
      sub_agency?: string
    }
  }
  source_url?: string
  state?: string
  city?: string
  location?: {
    state?: string
    city?: string
    address?: string
  }
  // Additional event-specific fields
  [key: string]: any
}

export interface DynamicSignal {
  signal_type: string
  description: string
  evidence_quote?: string
}

// ============================================================================
// Lead Types
// ============================================================================

export interface LeadCurrent {
  id: number
  entity_id: number
  score: number
  confidence_score: number
  status: LeadStatus
  reasons: LeadReasons
  last_updated_at: string
}

export interface LocationLead {
  id: number
  entity_id: number
  state: string  // 2-letter state code (FL, CA, TX, etc.)
  city: string | null
  score: number
  confidence_score: number
  status: LeadStatus
  event_count: number
  reasons: LeadReasons
  last_event_date: string | null
  created_at: string
  last_updated_at: string
}

// Reason value can be either a simple number or an object with count and score
export type ReasonValue = number | { count: number; score: number }

export interface LeadReasons {
  // Event type scores (can be number or {count, score} object)
  funding_round?: ReasonValue
  hiring_surge?: ReasonValue
  partnership?: ReasonValue
  expansion?: ReasonValue
  product_launch?: ReasonValue
  acquisition?: ReasonValue
  leadership_change?: ReasonValue
  award_recognition?: ReasonValue
  government_contract?: ReasonValue
  demolition?: ReasonValue
  permit?: ReasonValue

  // Evidence
  evidence_event_ids?: string[]
  total_events?: number

  // Additional dynamic reasons
  [key: string]: ReasonValue | string[] | number | undefined
}

export type LeadStatus = 'NEW' | 'ACTIVE' | 'STALE' | 'DISMISSED' | 'CONTACTED' | 'QUALIFIED' | 'CONVERTED'

export interface LeadStateHistory {
  id: number
  entity_id: number
  score: number
  confidence_score: number
  status: LeadStatus
  reasons: LeadReasons
  changed_at: string
}

// ============================================================================
// Combined View Types (for API responses)
// ============================================================================

export interface LeadWithEntity extends LocationLead {
  entity: Entity
  latest_event?: Event | null  // Optional latest event for government opportunities
}

export interface LeadDetailView extends LeadWithEntity {
  events: Event[]
}

// ============================================================================
// API Response Types
// ============================================================================

export interface LeadsListResponse {
  leads: LeadWithEntity[]
  total: number
  limit: number
  offset: number
}

export interface LeadDetailResponse {
  lead: LeadWithEntity
  events: Event[]
}

export interface DashboardStatsResponse {
  totalLeads: number
  newThisWeek: number
  avgScore: number
  dailyLimitUsed: number
  dailyLimitMax: number
  stateBreakdown: StateStats[]
  recentActivity: RecentActivity[]
}

export interface StateStats {
  state: string
  count: number
  avgScore: number
}

export interface RecentActivity {
  entity_name: string
  event_type: string
  state: string
  time_ago: string
  score: number
}

// ============================================================================
// Filter Types
// ============================================================================

export interface LeadFilters {
  states?: string[]
  status?: LeadStatus[]
  minScore?: number
  maxScore?: number
  search?: string
  limit?: number
  offset?: number
}

// ============================================================================
// User Management Types
// ============================================================================

export interface User {
  id: string
  auth_user_id: string
  email: string
  full_name: string
  is_active: boolean
  is_verified: boolean
  avatar_url: string | null
  phone: string | null
  title: string | null
  department: string | null
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface Role {
  id: number
  name: string
  display_name: string
  description: string
  permissions: RolePermissions
  created_at: string
}

export interface RolePermissions {
  can_view_leads: boolean
  can_export_leads: boolean
  can_view_all_states: boolean
  can_manage_users: boolean
  can_view_analytics: boolean
  can_manage_settings: boolean
  max_daily_leads: number  // -1 = unlimited
}

export interface UserPermissions {
  id: number
  user_id: string
  role_id: number
  allowed_states: string[] | null  // null = all states
  max_daily_leads: number | null  // null = use role default
  custom_permissions: Partial<RolePermissions>
  access_starts_at: string | null
  access_expires_at: string | null
  assigned_by: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface UserWithPermissions extends User {
  permissions: UserPermissions
  role: Role
}
