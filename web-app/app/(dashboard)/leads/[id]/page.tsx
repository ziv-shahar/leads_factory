'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { EventTimeline } from '@/components/leads/event-timeline'
import { Button } from '@/components/ui/button'
import {
  ArrowLeft,
  Building2,
  MapPin,
  Globe,
  Linkedin,
  Download,
  ExternalLink,
  Loader2,
  Calendar,
  TrendingUp,
  FileText,
  DollarSign,
  Ruler,
} from 'lucide-react'
import type { LeadWithEntity, Event } from '@/types/database'
import { formatDistanceToNow, format } from 'date-fns'
import { cn } from '@/lib/utils/cn'
import Link from 'next/link'
import {
  formatDeadlineWithCountdown,
  getDeadlineUrgency,
  getUrgencyColor,
  type OpportunityData
} from '@/lib/utils/opportunity'

export default function LeadDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [lead, setLead] = useState<LeadWithEntity | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (params.id) {
      fetchLeadDetail()
    }
  }, [params.id])

  async function fetchLeadDetail() {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/location-leads/${params.id}`, {
        cache: 'no-store' // Disable caching to ensure fresh data
      })
      const data = await response.json()

      if (response.ok) {
        setLead(data.lead)
        setEvents(data.events || [])
      } else {
        setError(data.error || 'Failed to load lead details')
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    // TODO: Implement export with access logging
    console.log('Export lead:', lead)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (error || !lead) {
    return (
      <div className="text-center py-12">
        <div className="max-w-md mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            Lead Not Found
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">{error || 'This lead does not exist'}</p>
          <Button onClick={() => router.push('/leads')} variant="outline">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Leads
          </Button>
        </div>
      </div>
    )
  }

  const { entity } = lead

  // Check if this is a government opportunity
  const isGovernmentOpportunity = entity.entity_type === 'government_agency'

  // Extract opportunity data from the first event (if it exists)
  const opportunityEvent = isGovernmentOpportunity && events.length > 0 ? events[0] : null

  // Type guard function to narrow key_facts union type
  type KeyFactsObject = Exclude<NonNullable<Event['strict']>['key_facts'], string[]>
  const isKeyFactsObject = (kf: any): kf is KeyFactsObject =>
    kf != null && typeof kf === 'object' && !Array.isArray(kf)

  const keyFacts = opportunityEvent?.strict?.key_facts
  const opportunityData: OpportunityData | undefined =
    keyFacts && isKeyFactsObject(keyFacts) ? {
      solicitation_number: keyFacts.other?.solicitation_number,
      response_deadline: keyFacts.other?.response_deadline,
      opportunity_status: keyFacts.other?.opportunity_status,
      notice_type: keyFacts.other?.notice_type,
      aboa_sf_min: keyFacts.aboa_sf_min,
      aboa_sf_max: keyFacts.aboa_sf_max,
      amount: keyFacts.amount,
      delineated_area: keyFacts.other?.delineated_area,
      lease_term_years: keyFacts.other?.lease_term_years,
      firm_term_years: keyFacts.other?.firm_term_years,
      parking_spaces: keyFacts.other?.parking_spaces,
      facility_security_level: keyFacts.other?.facility_security_level,
      sub_agency: keyFacts.other?.sub_agency,
    } : undefined

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-300'
      case 'NEW':
        return 'bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-300'
      case 'CONTACTED':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
      case 'QUALIFIED':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
      default:
        return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
    }
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link
          href="/dashboard"
          className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        >
          Dashboard
        </Link>
        <span className="text-gray-400">/</span>
        <Link
          href="/leads"
          className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        >
          Leads
        </Link>
        <span className="text-gray-400">/</span>
        <span className="text-gray-900 dark:text-white font-medium">
          {entity.canonical_name}
        </span>
      </div>

      {/* Header Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4 flex-1">
            {/* Logo */}
            <div className="w-16 h-16 rounded-lg bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white font-bold text-2xl flex-shrink-0">
              {entity.canonical_name.charAt(0)}
            </div>

            {/* Company Info */}
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {entity.canonical_name}
              </h1>

              <div className="flex flex-wrap gap-3 text-sm text-gray-600 dark:text-gray-400">
                {entity.domain && (
                  <a
                    href={`https://${entity.domain}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 hover:text-primary-600 dark:hover:text-primary-400"
                  >
                    <Globe className="h-4 w-4" />
                    {entity.domain}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}

                {entity.entity_type && (
                  <div className="flex items-center gap-1">
                    <Building2 className="h-4 w-4" />
                    <span className="capitalize">{entity.entity_type.replace(/_/g, ' ')}</span>
                  </div>
                )}

                <div className="flex items-center gap-1">
                  <MapPin className="h-4 w-4" />
                  {lead.city ? `${lead.city}, ${lead.state}` : lead.state}
                </div>
              </div>

              {/* Entity Metadata */}
              <div className="mt-4 flex flex-wrap gap-4 text-sm">
                {entity.entity_metadata.website_url && entity.entity_metadata.website_url !== `https://${entity.domain}` && (
                  <a
                    href={entity.entity_metadata.website_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
                  >
                    Website
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}

                {entity.entity_metadata.linkedin_url && (
                  <a
                    href={entity.entity_metadata.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
                  >
                    <Linkedin className="h-4 w-4" />
                    LinkedIn
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}

                {entity.entity_metadata.industry && (
                  <span className="text-gray-700 dark:text-gray-300">
                    Industry: {entity.entity_metadata.industry}
                  </span>
                )}

                {entity.entity_metadata.employee_count && (
                  <span className="text-gray-700 dark:text-gray-300">
                    Employees: {entity.entity_metadata.employee_count}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 flex-shrink-0">
            <Button onClick={() => router.push('/leads')} variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <Button onClick={handleExport} variant="outline" size="sm" className="gap-2">
              <Download className="h-4 w-4" />
              Export
            </Button>
          </div>
        </div>

        {/* Metrics Row */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          {isGovernmentOpportunity && opportunityData ? (
            // Government Opportunity Metrics
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* Status */}
              <div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">Status</p>
                <span className={cn('inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium', getStatusColor(lead.status))}>
                  {lead.status}
                </span>
              </div>

              {/* Deadline */}
              {opportunityData.response_deadline && (
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">Deadline</p>
                  {(() => {
                    const deadlineInfo = formatDeadlineWithCountdown(opportunityData.response_deadline)
                    const urgency = getDeadlineUrgency(opportunityData.response_deadline)
                    return (
                      <div>
                        <div className="text-sm font-bold text-gray-900 dark:text-white">
                          {deadlineInfo.formatted}
                        </div>
                        <div className={cn('text-xs font-semibold mt-1', getUrgencyColor(urgency).split(' ')[0].replace('bg-', 'text-'))}>
                          ({deadlineInfo.countdown})
                        </div>
                      </div>
                    )
                  })()}
                </div>
              )}

              {/* Size */}
              {(opportunityData.aboa_sf_min || opportunityData.aboa_sf_max) && (
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">Size</p>
                  <div className="text-sm font-bold text-gray-900 dark:text-white">
                    {opportunityData.aboa_sf_min && opportunityData.aboa_sf_max
                      ? `${opportunityData.aboa_sf_min.toLocaleString()}-${opportunityData.aboa_sf_max.toLocaleString()} sq ft`
                      : opportunityData.aboa_sf_min
                      ? `${opportunityData.aboa_sf_min.toLocaleString()}+ sq ft`
                      : `Up to ${opportunityData.aboa_sf_max?.toLocaleString()} sq ft`
                    }
                  </div>
                </div>
              )}

              {/* Budget */}
              {opportunityData.amount && (
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">Budget</p>
                  <div className="text-sm font-bold text-gray-900 dark:text-white">
                    {opportunityData.amount}
                  </div>
                </div>
              )}
            </div>
          ) : (
            // Business Event Metrics
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {/* Status */}
              <div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">Status</p>
                <span className={cn('inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium', getStatusColor(lead.status))}>
                  {lead.status}
                </span>
              </div>

              {/* Events */}
              <div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">Signals</p>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-gray-500" />
                  <span className="text-lg font-semibold text-gray-900 dark:text-white">
                    {lead.event_count}
                  </span>
                </div>
              </div>

              {/* Last Activity */}
              <div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">Last Activity</p>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-500" />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {lead.last_event_date
                      ? formatDistanceToNow(new Date(lead.last_event_date), { addSuffix: true })
                      : 'Unknown'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Sidebar - Opportunity Details or Metadata */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 sticky top-6">
            {isGovernmentOpportunity && opportunityData ? (
              // Government Opportunity Details
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Opportunity Details
                </h3>
                <dl className="space-y-4">
                  {opportunityData.solicitation_number && (
                    <div>
                      <dt className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                        Solicitation
                      </dt>
                      <dd className="text-sm font-mono font-semibold text-gray-900 dark:text-white">
                        {opportunityData.solicitation_number}
                      </dd>
                    </div>
                  )}

                  {opportunityData.sub_agency && (
                    <div>
                      <dt className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                        Sub-Agency
                      </dt>
                      <dd className="text-sm font-medium text-gray-900 dark:text-white">
                        {opportunityData.sub_agency}
                      </dd>
                    </div>
                  )}

                  {opportunityData.notice_type && (
                    <div>
                      <dt className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                        Notice Type
                      </dt>
                      <dd className="text-sm font-medium text-gray-900 dark:text-white">
                        {opportunityData.notice_type}
                      </dd>
                    </div>
                  )}

                  {opportunityData.delineated_area && (
                    <div>
                      <dt className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                        Delineated Area
                      </dt>
                      <dd className="text-sm font-medium text-gray-900 dark:text-white">
                        {opportunityData.delineated_area}
                      </dd>
                    </div>
                  )}

                  {opportunityData.lease_term_years && (
                    <div>
                      <dt className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                        Lease Terms
                      </dt>
                      <dd className="text-sm font-medium text-gray-900 dark:text-white">
                        {opportunityData.lease_term_years} year lease
                        {opportunityData.firm_term_years && ` (${opportunityData.firm_term_years} year firm term)`}
                      </dd>
                    </div>
                  )}

                  {opportunityData.parking_spaces && (
                    <div>
                      <dt className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                        Parking
                      </dt>
                      <dd className="text-sm font-medium text-gray-900 dark:text-white">
                        {opportunityData.parking_spaces} spaces required
                      </dd>
                    </div>
                  )}

                  {opportunityData.facility_security_level && (
                    <div>
                      <dt className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                        Security Level
                      </dt>
                      <dd className="text-sm font-medium text-gray-900 dark:text-white">
                        Level {opportunityData.facility_security_level}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>
            ) : (
              // Business Event Summary
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Lead Summary
                </h3>
                <div className="space-y-3">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {lead.event_count} signal{lead.event_count !== 1 ? 's' : ''} detected for this lead.
                  </p>
                  {entity.entity_metadata.industry && (
                    <div>
                      <dt className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                        Industry
                      </dt>
                      <dd className="text-sm font-medium text-gray-900 dark:text-white">
                        {entity.entity_metadata.industry}
                      </dd>
                    </div>
                  )}
                  {entity.entity_metadata.employee_count && (
                    <div>
                      <dt className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                        Company Size
                      </dt>
                      <dd className="text-sm font-medium text-gray-900 dark:text-white">
                        {entity.entity_metadata.employee_count}+ employees
                      </dd>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Additional Metadata */}
            {Object.keys(entity.entity_metadata).length > 0 && (
              <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                  Additional Information
                </h3>
                <dl className="space-y-2">
                  {Object.entries(entity.entity_metadata)
                    .filter(([key]) => !['website_url', 'linkedin_url', 'industry', 'employee_count', 'hq_city', 'hq_state'].includes(key))
                    .map(([key, value]) => (
                      <div key={key} className="text-xs">
                        <dt className="text-gray-600 dark:text-gray-400 capitalize">
                          {key.replace(/_/g, ' ')}
                        </dt>
                        <dd className="text-gray-900 dark:text-white font-medium mt-0.5">
                          {Array.isArray(value) ? value.join(', ') : String(value)}
                        </dd>
                      </div>
                    ))}
                </dl>
              </div>
            )}

            {/* Timestamps */}
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-600 dark:text-gray-400 space-y-1">
              <p>
                Created: {format(new Date(lead.created_at), 'MMM d, yyyy')}
              </p>
              <p>
                Updated: {format(new Date(lead.last_updated_at), 'MMM d, yyyy')}
              </p>
              {entity.last_enriched_at && (
                <p>
                  Enriched: {format(new Date(entity.last_enriched_at), 'MMM d, yyyy')}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Right Content - Event Timeline */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
              Event Timeline
              <span className="ml-2 text-sm font-normal text-gray-600 dark:text-gray-400">
                ({events.length} event{events.length !== 1 ? 's' : ''})
              </span>
            </h2>

            <EventTimeline events={events} />
          </div>
        </div>
      </div>
    </div>
  )
}
