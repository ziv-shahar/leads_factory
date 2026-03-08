/**
 * Utility functions for government opportunities
 */

import { differenceInDays, formatDistanceToNow, parseISO, format } from 'date-fns'

export interface OpportunityData {
  opportunity_id?: string
  solicitation_number?: string
  response_deadline?: string
  opportunity_status?: string
  notice_type?: string
  aboa_sf_min?: number
  aboa_sf_max?: number
  amount?: string
  delineated_area?: string
  lease_term_years?: number
  firm_term_years?: number
  parking_spaces?: number
  facility_security_level?: string
  sub_agency?: string
  temporal_status?: string
}

/**
 * Calculate days until deadline
 */
export function getDaysUntilDeadline(deadline: string): number {
  try {
    const deadlineDate = parseISO(deadline)
    const now = new Date()
    return differenceInDays(deadlineDate, now)
  } catch {
    return 0
  }
}

/**
 * Format deadline with countdown
 */
export function formatDeadlineWithCountdown(deadline: string): { formatted: string; countdown: string; daysRemaining: number } {
  try {
    const deadlineDate = parseISO(deadline)
    const daysRemaining = getDaysUntilDeadline(deadline)

    return {
      formatted: format(deadlineDate, 'MMM d, yyyy'),
      countdown: daysRemaining >= 0
        ? `${daysRemaining} day${daysRemaining !== 1 ? 's' : ''}`
        : `${Math.abs(daysRemaining)} day${Math.abs(daysRemaining) !== 1 ? 's' : ''} ago`,
      daysRemaining
    }
  } catch {
    return {
      formatted: 'TBD',
      countdown: 'TBD',
      daysRemaining: 999
    }
  }
}

/**
 * Get deadline urgency level
 */
export function getDeadlineUrgency(deadline: string): 'urgent' | 'warning' | 'normal' | 'expired' {
  const days = getDaysUntilDeadline(deadline)

  if (days < 0) return 'expired'
  if (days < 7) return 'urgent'
  if (days < 14) return 'warning'
  return 'normal'
}

/**
 * Get status badge color
 */
export function getOpportunityStatusColor(status: string): string {
  const statusLower = status?.toLowerCase() || ''

  switch (statusLower) {
    case 'active':
      return 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700'
    case 'forecasted':
    case 'pre_solicitation':
      return 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700'
    case 'awarded':
    case 'completed':
      return 'bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-900/30 dark:text-gray-300 dark:border-gray-700'
    case 'closed':
    case 'cancelled':
      return 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700'
    default:
      return 'bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-900/30 dark:text-gray-300 dark:border-gray-700'
  }
}

/**
 * Get urgency badge color
 */
export function getUrgencyColor(urgency: 'urgent' | 'warning' | 'normal' | 'expired'): string {
  switch (urgency) {
    case 'urgent':
      return 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700'
    case 'warning':
      return 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700'
    case 'expired':
      return 'bg-gray-50 text-gray-500 border-gray-200 dark:bg-gray-900/30 dark:text-gray-400 dark:border-gray-700'
    default:
      return 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700'
  }
}

/**
 * Format square footage range
 */
export function formatSquareFootage(min?: number, max?: number): string {
  if (!min && !max) return 'TBD'
  if (min && max) {
    if (min === max) return `${min.toLocaleString()} sq ft`
    return `${min.toLocaleString()}-${max.toLocaleString()} sq ft`
  }
  if (min) return `${min.toLocaleString()}+ sq ft`
  if (max) return `Up to ${max.toLocaleString()} sq ft`
  return 'TBD'
}

/**
 * Format budget amount
 */
export function formatBudget(amount?: string): string {
  if (!amount) return 'TBD'

  // If already formatted (has $ or commas), return as-is
  if (amount.includes('$') || amount.includes(',')) {
    return amount
  }

  // Try to parse as number and format as currency
  const numericAmount = parseFloat(amount)
  if (isNaN(numericAmount)) {
    return amount // Return original if not a number
  }

  // Format as currency with commas and 2 decimal places
  return `$${numericAmount.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`
}

/**
 * Map SAM.gov status to display status
 */
export function mapOpportunityStatus(status?: string): string {
  if (!status) return 'UNKNOWN'

  const statusLower = status.toLowerCase()
  switch (statusLower) {
    case 'active':
      return 'ACTIVE'
    case 'forecasted':
      return 'FORECASTED'
    case 'pre_solicitation':
      return 'PRE-SOLICITATION'
    case 'awarded':
      return 'AWARDED'
    case 'completed':
      return 'COMPLETED'
    case 'closed':
      return 'CLOSED'
    case 'cancelled':
      return 'CANCELLED'
    default:
      return status.toUpperCase()
  }
}
