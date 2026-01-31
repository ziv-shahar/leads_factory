'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { EventTimeline } from '@/components/leads/event-timeline'
import { ScoreBreakdown } from '@/components/leads/score-breakdown'
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
} from 'lucide-react'
import type { LeadWithEntity, Event } from '@/types/database'
import { formatDistanceToNow, format } from 'date-fns'
import { cn } from '@/lib/utils/cn'
import Link from 'next/link'

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
      const response = await fetch(`/api/location-leads/${params.id}`)
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

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-success-600 dark:text-success-400 bg-success-100 dark:bg-success-900/30'
    if (score >= 60) return 'text-primary-600 dark:text-primary-400 bg-primary-100 dark:bg-primary-900/30'
    if (score >= 40) return 'text-warning-600 dark:text-warning-400 bg-warning-100 dark:bg-warning-900/30'
    return 'text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-700'
  }

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
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700 grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Score */}
          <div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Lead Score</p>
            <div className={cn('inline-flex items-center px-3 py-1.5 rounded-lg text-lg font-bold', getScoreColor(lead.score))}>
              {lead.score}
            </div>
          </div>

          {/* Status */}
          <div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Status</p>
            <span className={cn('inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium', getStatusColor(lead.status))}>
              {lead.status}
            </span>
          </div>

          {/* Events */}
          <div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Events</p>
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-gray-500" />
              <span className="text-lg font-semibold text-gray-900 dark:text-white">
                {lead.event_count}
              </span>
            </div>
          </div>

          {/* Last Activity */}
          <div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Last Activity</p>
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

        {/* Confidence Score */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Confidence Score</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {Math.round(lead.confidence_score * 100)}%
            </span>
          </div>
          <div className="mt-2 w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-500 dark:bg-primary-600 rounded-full transition-all"
              style={{ width: `${lead.confidence_score * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Sidebar - Score Breakdown */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 sticky top-6">
            <ScoreBreakdown reasons={lead.reasons} totalScore={lead.score} />

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
