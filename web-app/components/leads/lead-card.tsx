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
    <Link href={`/leads/${lead.id}`} className="block h-full">
      <div
        className={cn(
          'h-full bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-100 dark:border-gray-700',
          'hover:border-primary-400 dark:hover:border-primary-500 hover:shadow-2xl',
          'transition-all duration-300 cursor-pointer p-6 group',
          'flex flex-col',
          className
        )}
      >
        {/* Header with Score Badge */}
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-start gap-4 flex-1 min-w-0">
            {/* Logo/Icon */}
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary-500 via-primary-600 to-secondary-600 flex items-center justify-center text-white font-bold text-xl flex-shrink-0 group-hover:scale-110 group-hover:rotate-3 transition-all duration-300 shadow-lg">
              {entity.canonical_name.charAt(0)}
            </div>

            {/* Company Info */}
            <div className="flex-1 min-w-0">
              <h3 className="font-bold text-gray-900 dark:text-white text-xl mb-1 truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                {entity.canonical_name}
              </h3>
              {entity.domain && (
                <p className="text-sm text-gray-500 dark:text-gray-400 truncate flex items-center gap-1.5">
                  <span className="font-medium">{entity.domain}</span>
                  <ExternalLink className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                </p>
              )}
            </div>
          </div>

          {/* Score Badge - Large and Prominent */}
          <div className="flex flex-col items-end flex-shrink-0 ml-4">
            <div className={cn(
              'inline-flex items-center justify-center w-16 h-16 rounded-2xl text-2xl font-black shadow-lg',
              'group-hover:scale-110 transition-transform duration-300',
              getScoreColor(lead.score)
            )}>
              {lead.score}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 font-semibold tracking-wide">
              SCORE
            </p>
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 gap-3 mb-5">
          <div className="flex items-center gap-2 text-sm">
            <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
              <MapPin className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">Location</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                {lead.city ? `${lead.city}, ${lead.state}` : lead.state}
              </p>
            </div>
          </div>

          {entity.entity_type && (
            <div className="flex items-center gap-2 text-sm">
              <div className="w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0">
                <Building2 className="h-4 w-4 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="min-w-0">
                <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">Type</p>
                <p className="text-sm font-semibold text-gray-900 dark:text-white truncate capitalize">
                  {entity.entity_type.replace(/_/g, ' ')}
                </p>
              </div>
            </div>
          )}

          <div className="flex items-center gap-2 text-sm">
            <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0">
              <TrendingUp className="h-4 w-4 text-green-600 dark:text-green-400" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">Events</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">
                {lead.event_count} signal{lead.event_count !== 1 ? 's' : ''}
              </p>
            </div>
          </div>

          {lead.last_event_date && (
            <div className="flex items-center gap-2 text-sm">
              <div className="w-8 h-8 rounded-lg bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center flex-shrink-0">
                <Calendar className="h-4 w-4 text-orange-600 dark:text-orange-400" />
              </div>
              <div className="min-w-0">
                <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">Last Activity</p>
                <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                  {formatDistanceToNow(new Date(lead.last_event_date), { addSuffix: true })}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Event Type Signals - More Prominent */}
        {topReasons.length > 0 && (
          <div className="mb-5">
            <p className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
              Top Signals
            </p>
            <div className="flex flex-col gap-2">
              {topReasons.map(([type, score], idx) => (
                <div
                  key={type}
                  className={cn(
                    'flex items-center justify-between px-3 py-2 rounded-lg',
                    'bg-gradient-to-r transition-all duration-200',
                    idx === 0 && 'from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20',
                    idx === 1 && 'from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20',
                    idx === 2 && 'from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20',
                    'hover:scale-105 hover:shadow-md'
                  )}
                >
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-200 capitalize">
                    {type.replace(/_/g, ' ')}
                  </span>
                  <span className={cn(
                    'text-sm font-black',
                    idx === 0 && 'text-primary-700 dark:text-primary-300',
                    idx === 1 && 'text-blue-700 dark:text-blue-300',
                    idx === 2 && 'text-purple-700 dark:text-purple-300'
                  )}>
                    +{score}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer - Push to bottom */}
        <div className="mt-auto pt-5 border-t-2 border-gray-100 dark:border-gray-700 flex items-center justify-between">
          <span className={cn(
            'inline-flex items-center px-4 py-2 rounded-lg text-sm font-bold uppercase tracking-wide',
            'shadow-sm',
            getStatusColor(lead.status)
          )}>
            {lead.status}
          </span>

          {/* Confidence Score */}
          <div className="text-right">
            <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mb-0.5">Confidence</p>
            <p className="text-lg font-black text-gray-900 dark:text-white">
              {Math.round(lead.confidence_score * 100)}%
            </p>
          </div>
        </div>
      </div>
    </Link>
  )
}
