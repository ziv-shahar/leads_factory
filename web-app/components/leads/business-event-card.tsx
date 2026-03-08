'use client'

import { LeadWithEntity } from '@/types/database'
import { Building2, MapPin, TrendingUp, Calendar, Globe, Users, DollarSign, Briefcase, Rocket } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { cn } from '@/lib/utils/cn'
import Link from 'next/link'

interface BusinessEventCardProps {
  lead: LeadWithEntity
  className?: string
}

// Event type icon mapping
const EVENT_TYPE_CONFIG: Record<string, { icon: any; color: string; gradient: string }> = {
  expansion: {
    icon: TrendingUp,
    color: 'text-green-600 dark:text-green-400',
    gradient: 'from-green-500 to-emerald-600'
  },
  funding_round: {
    icon: DollarSign,
    color: 'text-emerald-600 dark:text-emerald-400',
    gradient: 'from-emerald-500 to-green-600'
  },
  partnership: {
    icon: Briefcase,
    color: 'text-purple-600 dark:text-purple-400',
    gradient: 'from-purple-500 to-indigo-600'
  },
  product_launch: {
    icon: Rocket,
    color: 'text-indigo-600 dark:text-indigo-400',
    gradient: 'from-indigo-500 to-purple-600'
  },
  hiring_surge: {
    icon: Users,
    color: 'text-blue-600 dark:text-blue-400',
    gradient: 'from-blue-500 to-indigo-600'
  },
  acquisition: {
    icon: Building2,
    color: 'text-red-600 dark:text-red-400',
    gradient: 'from-red-500 to-pink-600'
  },
  leadership_change: {
    icon: Users,
    color: 'text-orange-600 dark:text-orange-400',
    gradient: 'from-orange-500 to-red-600'
  },
  award_recognition: {
    icon: TrendingUp,
    color: 'text-yellow-600 dark:text-yellow-400',
    gradient: 'from-yellow-500 to-orange-600'
  },
  default: {
    icon: Building2,
    color: 'text-gray-600 dark:text-gray-400',
    gradient: 'from-gray-500 to-gray-600'
  }
}

export function BusinessEventCard({ lead, className }: BusinessEventCardProps) {
  const { entity } = lead

  // Get top event type from reasons
  const topEventType = Object.entries(lead.reasons)
    .filter(([key]) => key !== 'evidence_event_ids' && key !== 'total_events')
    .map(([key, value]) => {
      const score = typeof value === 'object' && value !== null && 'score' in value
        ? (value as any).score
        : typeof value === 'number'
        ? value
        : 0
      return [key, score] as [string, number]
    })
    .sort(([, a], [, b]) => b - a)[0]

  const eventType = topEventType ? topEventType[0] : 'default'
  const config = EVENT_TYPE_CONFIG[eventType] || EVENT_TYPE_CONFIG.default
  const Icon = config.icon

  // Display label - show entity type or "NEW LEAD" instead of "DEFAULT"
  const displayLabel = eventType === 'default'
    ? (entity.entity_type ? entity.entity_type.replace(/_/g, ' ') : 'NEW LEAD')
    : eventType.replace(/_/g, ' ')

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
          'transition-all duration-300 cursor-pointer group',
          'flex flex-col',
          className
        )}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-gray-100 dark:border-gray-700">
          <div className="flex items-start gap-4 mb-3">
            {/* Dynamic Event Icon */}
            <div className={cn(
              'w-14 h-14 rounded-xl bg-gradient-to-br flex items-center justify-center text-white flex-shrink-0',
              'group-hover:scale-110 group-hover:rotate-3 transition-all duration-300 shadow-lg',
              config.gradient
            )}>
              <Icon className="h-7 w-7" />
            </div>

            {/* Company Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="font-bold text-gray-900 dark:text-white text-xl truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                  {entity.canonical_name}
                </h3>
                {/* Event Type Badge */}
                <div className={cn(
                  'inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wide',
                  'bg-gradient-to-r shadow-sm flex-shrink-0',
                  config.gradient,
                  'text-white'
                )}>
                  {displayLabel}
                </div>
              </div>
              {entity.domain && (
                <p className="text-sm text-gray-500 dark:text-gray-400 truncate flex items-center gap-1.5 mb-2">
                  <Globe className="h-3.5 w-3.5" />
                  <span>{entity.domain}</span>
                </p>
              )}
              {/* Event Summary */}
              <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2 leading-relaxed">
                {eventType === 'expansion' && `Expanding operations in ${lead.city ? `${lead.city}, ` : ''}${lead.state}`}
                {eventType === 'funding_round' && 'Recent funding round announced'}
                {eventType === 'partnership' && 'New strategic partnership formed'}
                {eventType === 'product_launch' && 'New product or service launched'}
                {eventType === 'hiring_surge' && 'Actively hiring and growing team'}
                {eventType === 'acquisition' && 'Acquisition or merger activity'}
                {eventType === 'leadership_change' && 'Leadership team expansion'}
                {eventType === 'award_recognition' && 'Award or recognition received'}
                {!EVENT_TYPE_CONFIG[eventType] && 'Business activity detected'}
              </p>
            </div>
          </div>
        </div>

        {/* Company Details */}
        <div className="px-6 pb-5">
          {/* Location - Prominent Display */}
          <div className="flex items-center gap-2 mb-4 p-3 rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-800/30">
            <div className="w-9 h-9 rounded-lg bg-blue-500 dark:bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm">
              <MapPin className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-xs text-blue-600 dark:text-blue-400 font-semibold uppercase tracking-wide">Location</p>
              <p className="text-sm font-bold text-gray-900 dark:text-white">
                {lead.city ? `${lead.city}, ${lead.state}` : lead.state}
              </p>
            </div>
          </div>

          {/* Company Metadata */}
          {(entity.entity_metadata?.industry || entity.entity_metadata?.employee_count) && (
            <div className="flex flex-col gap-2 mb-4">
              {entity.entity_metadata.industry && (
                <div className="flex items-center gap-2 text-sm">
                  <Building2 className="h-4 w-4 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300 font-medium">
                    {entity.entity_metadata.industry}
                  </span>
                </div>
              )}
              {entity.entity_metadata.employee_count && (
                <div className="flex items-center gap-2 text-sm">
                  <Users className="h-4 w-4 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300 font-medium">
                    {entity.entity_metadata.employee_count}+ employees
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="pt-4 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between">
            <span className={cn(
              'inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide',
              getStatusColor(lead.status)
            )}>
              {lead.status}
            </span>

            <span className="text-xs font-semibold text-primary-600 dark:text-primary-400 group-hover:underline">
              View Details →
            </span>
          </div>
        </div>
      </div>
    </Link>
  )
}
