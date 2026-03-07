'use client'

import { LeadWithEntity } from '@/types/database'
import { GovernmentOpportunityCard } from './government-opportunity-card'
import { BusinessEventCard } from './business-event-card'
import { OpportunityData } from '@/lib/utils/opportunity'

interface LeadCardRouterProps {
  lead: LeadWithEntity
  opportunityData?: OpportunityData
  className?: string
}

/**
 * Smart card router that selects the appropriate card component
 * based on the lead type and filters out irrelevant lead types
 */
export function LeadCardRouter({ lead, opportunityData, className }: LeadCardRouterProps) {
  const { entity, reasons } = lead

  // Filter out permits and demolitions
  const hasPermit = 'permit' in reasons && reasons.permit
  const hasDemolition = 'demolition' in reasons && reasons.demolition

  // Only show if NOT primarily a permit or demolition lead
  // (If they have other events too, we still show them)
  const totalReasons = Object.keys(reasons).filter(
    key => key !== 'evidence_event_ids' && key !== 'total_events'
  ).length

  // If ONLY permit or ONLY demolition, don't show
  if (totalReasons === 1 && (hasPermit || hasDemolition)) {
    return null
  }

  // Determine if this is a government opportunity
  const isGovernmentOpportunity =
    entity.entity_type === 'government_agency' ||
    opportunityData?.opportunity_id ||
    'government_contract' in reasons

  // Route to appropriate card
  if (isGovernmentOpportunity) {
    return (
      <GovernmentOpportunityCard
        lead={lead}
        opportunityData={opportunityData}
        className={className}
      />
    )
  }

  // Default to business event card
  return <BusinessEventCard lead={lead} className={className} />
}
