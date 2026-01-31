'use client'

import { LeadWithEntity } from '@/types/database'
import { Building2, MapPin, TrendingUp, Calendar, ExternalLink } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { cn } from '@/lib/utils/cn'
import Link from 'next/link'

interface LeadCardProps {
  lead: LeadWithEntity
  className?: string
}

export function LeadCard({ lead, className }: LeadCardProps) {
  const { entity } = lead

  // Get top 3 event types from reasons (exclude evidence_event_ids and total_events)
  // Handle both number values and {count, score} objects
  const topReasons = Object.entries(lead.reasons)
    .filter(([key]) => key !== 'evidence_event_ids' && key !== 'total_events')
    .map(([key, value]) => {
      // Handle both number and object formats
      const score = typeof value === 'object' && value !== null && 'score' in value
        ? (value as any).score
        : typeof value === 'number'
        ? value
        : 0
      return [key, score] as [string, number]
    })
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)

  // Determine score color
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-300'
    if (score >= 60) return 'bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-300'
    if (score >= 40) return 'bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-300'
    return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
  }

  // Determine status color
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
    <Link href={`/leads/${lead.id}`}>
      <div
        className={cn(
          'bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-lg hover:border-primary-300 dark:hover:border-primary-600 transition-all cursor-pointer p-6 group',
          className
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            {/* Logo/Icon */}
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white font-bold text-lg flex-shrink-0 group-hover:scale-105 transition-transform">
              {entity.canonical_name.charAt(0)}
            </div>

            {/* Company Info */}
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-gray-900 dark:text-white text-lg truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                {entity.canonical_name}
              </h3>
              {entity.domain && (
                <p className="text-sm text-gray-500 dark:text-gray-400 truncate flex items-center gap-1">
                  {entity.domain}
                  <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </p>
              )}
            </div>
          </div>

          {/* Score Badge */}
          <div className="text-right flex-shrink-0 ml-4">
            <div className={cn('inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold', getScoreColor(lead.score))}>
              {lead.score}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 whitespace-nowrap">
              Lead Score
            </p>
          </div>
        </div>

        {/* Metadata Row */}
        <div className="flex flex-wrap gap-3 mb-4 text-sm text-gray-600 dark:text-gray-400">
          <div className="flex items-center gap-1">
            <MapPin className="h-4 w-4 flex-shrink-0" />
            <span className="truncate">
              {lead.city ? `${lead.city}, ${lead.state}` : lead.state}
            </span>
          </div>

          {entity.entity_type && (
            <div className="flex items-center gap-1">
              <Building2 className="h-4 w-4 flex-shrink-0" />
              <span className="truncate capitalize">
                {entity.entity_type.replace(/_/g, ' ')}
              </span>
            </div>
          )}

          <div className="flex items-center gap-1">
            <TrendingUp className="h-4 w-4 flex-shrink-0" />
            <span>{lead.event_count} event{lead.event_count !== 1 ? 's' : ''}</span>
          </div>

          {lead.last_event_date && (
            <div className="flex items-center gap-1">
              <Calendar className="h-4 w-4 flex-shrink-0" />
              <span className="truncate">
                {formatDistanceToNow(new Date(lead.last_event_date), { addSuffix: true })}
              </span>
            </div>
          )}
        </div>

        {/* Event Type Reasons */}
        {topReasons.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {topReasons.map(([type, score]) => (
              <span
                key={type}
                className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md text-xs font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                {type.replace(/_/g, ' ')}: +{score}
              </span>
            ))}
          </div>
        )}

        {/* Footer with Status */}
        <div className="pt-4 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between">
          <span className={cn('inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium', getStatusColor(lead.status))}>
            {lead.status}
          </span>

          {/* Confidence Score */}
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {Math.round(lead.confidence_score * 100)}% confidence
          </span>
        </div>
      </div>
    </Link>
  )
}
