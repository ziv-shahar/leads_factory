'use client'

import { Event } from '@/types/database'
import { formatDistanceToNow, format } from 'date-fns'
import {
  TrendingUp,
  Users,
  Briefcase,
  Award,
  Building,
  FileText,
  DollarSign,
  Rocket,
  Target,
  Zap,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils/cn'

const EVENT_ICONS: Record<string, any> = {
  funding_round: DollarSign,
  hiring_surge: Users,
  partnership: Briefcase,
  award_recognition: Award,
  expansion: Building,
  product_launch: Rocket,
  acquisition: Target,
  government_contract: FileText,
  leadership_change: Users,
  demolition: Building,
  permit: FileText,
  default: Zap,
}

const EVENT_COLORS: Record<string, string> = {
  funding_round: 'bg-success-100 text-success-600 dark:bg-success-900/30 dark:text-success-400',
  hiring_surge: 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400',
  partnership: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
  award_recognition: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
  expansion: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
  product_launch: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400',
  acquisition: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
  government_contract: 'bg-teal-100 text-teal-600 dark:bg-teal-900/30 dark:text-teal-400',
  leadership_change: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400',
  demolition: 'bg-pink-100 text-pink-600 dark:bg-pink-900/30 dark:text-pink-400',
  permit: 'bg-cyan-100 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-400',
  default: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
}

interface EventTimelineProps {
  events: Event[]
  className?: string
}

export function EventTimeline({ events, className }: EventTimelineProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set())

  if (events.length === 0) {
    return (
      <div className={cn('text-center py-12', className)}>
        <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-400">No events found for this lead</p>
      </div>
    )
  }

  const toggleExpand = (eventId: string) => {
    const newExpanded = new Set(expandedEvents)
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId)
    } else {
      newExpanded.add(eventId)
    }
    setExpandedEvents(newExpanded)
  }

  return (
    <div className={cn('flow-root', className)}>
      <ul className="-mb-8">
        {events.map((event, eventIdx) => {
          const Icon = EVENT_ICONS[event.event_type] || EVENT_ICONS.default
          const colorClass = EVENT_COLORS[event.event_type] || EVENT_COLORS.default
          const isExpanded = expandedEvents.has(event.id)
          const hasDetails =
            event.strict.summary ||
            (event.strict.key_facts && (
              Array.isArray(event.strict.key_facts)
                ? event.strict.key_facts.length > 0
                : Object.keys(event.strict.key_facts).length > 0
            )) ||
            (event.dynamic_signals && event.dynamic_signals.length > 0)

          return (
            <li key={event.id}>
              <div className="relative pb-8">
                {/* Timeline Line */}
                {eventIdx !== events.length - 1 && (
                  <span
                    className="absolute left-5 top-5 -ml-px h-full w-0.5 bg-gray-200 dark:bg-gray-700"
                    aria-hidden="true"
                  />
                )}

                <div className="relative flex items-start space-x-3">
                  {/* Icon */}
                  <div
                    className={cn(
                      'relative flex h-10 w-10 items-center justify-center rounded-full flex-shrink-0',
                      colorClass
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </div>

                  {/* Content */}
                  <div className="min-w-0 flex-1">
                    <div
                      className={cn(
                        'bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4',
                        hasDetails && 'cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 transition-colors'
                      )}
                      onClick={() => hasDetails && toggleExpand(event.id)}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-semibold text-gray-900 dark:text-white capitalize">
                              {event.event_type.replace(/_/g, ' ')}
                            </h4>
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              from {event.source}
                            </span>
                          </div>

                          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 dark:text-gray-400">
                            <span>
                              {event.event_time
                                ? format(new Date(event.event_time), 'MMM d, yyyy')
                                : 'Date unknown'}
                            </span>
                            {event.event_time && (
                              <>
                                <span>•</span>
                                <span>
                                  {formatDistanceToNow(new Date(event.event_time), {
                                    addSuffix: true,
                                  })}
                                </span>
                              </>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                          {/* Confidence Badge */}
                          <span className="inline-flex items-center px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300">
                            {Math.round(event.extraction_confidence * 100)}% confident
                          </span>

                          {/* Expand/Collapse Button */}
                          {hasDetails && (
                            <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                              {isExpanded ? (
                                <ChevronUp className="h-4 w-4 text-gray-500" />
                              ) : (
                                <ChevronDown className="h-4 w-4 text-gray-500" />
                              )}
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Summary (Always Visible if exists) */}
                      {event.strict.summary && (
                        <p className="mt-3 text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                          {event.strict.summary}
                        </p>
                      )}

                      {/* Expanded Details */}
                      {isExpanded && (
                        <div className="mt-4 space-y-4 border-t border-gray-100 dark:border-gray-700 pt-4">
                          {/* Key Facts */}
                          {event.strict.key_facts && Array.isArray(event.strict.key_facts) && event.strict.key_facts.length > 0 && (
                            <div>
                              <h5 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Key Facts
                              </h5>
                              <ul className="space-y-1.5">
                                {event.strict.key_facts.map((fact, idx) => (
                                  <li
                                    key={idx}
                                    className="text-sm text-gray-600 dark:text-gray-400 flex items-start"
                                  >
                                    <span className="mr-2 text-primary-500 dark:text-primary-400">
                                      •
                                    </span>
                                    <span>{fact}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Dynamic Signals */}
                          {event.dynamic_signals && event.dynamic_signals.length > 0 && (
                            <div>
                              <h5 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Additional Signals
                              </h5>
                              <div className="space-y-2">
                                {event.dynamic_signals.map((signal, idx) => (
                                  <div
                                    key={idx}
                                    className="bg-gray-50 dark:bg-gray-700/50 rounded-md p-3"
                                  >
                                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 capitalize">
                                      {signal.signal_type.replace(/_/g, ' ')}
                                    </p>
                                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                      {signal.description}
                                    </p>
                                    {signal.evidence_quote && (
                                      <p className="text-xs text-gray-500 dark:text-gray-500 italic mt-2 pl-3 border-l-2 border-gray-300 dark:border-gray-600">
                                        "{signal.evidence_quote}"
                                      </p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Additional Event Data */}
                          {Object.keys(event.strict).filter(
                            key => !['summary', 'key_facts', 'source_url', 'state', 'city', 'location'].includes(key)
                          ).length > 0 && (
                            <div>
                              <h5 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Additional Details
                              </h5>
                              <div className="grid grid-cols-2 gap-2">
                                {Object.entries(event.strict)
                                  .filter(
                                    ([key]) =>
                                      !['summary', 'key_facts', 'source_url', 'state', 'city', 'location'].includes(
                                        key
                                      )
                                  )
                                  .map(([key, value]) => (
                                    <div key={key} className="text-xs">
                                      <span className="text-gray-500 dark:text-gray-400 capitalize">
                                        {key.replace(/_/g, ' ')}:
                                      </span>{' '}
                                      <span className="text-gray-700 dark:text-gray-300">
                                        {typeof value === 'object'
                                          ? JSON.stringify(value)
                                          : String(value)}
                                      </span>
                                    </div>
                                  ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Source Link */}
                      {event.strict.source_url && (
                        <a
                          href={event.strict.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 mt-3 text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium"
                          onClick={e => e.stopPropagation()}
                        >
                          View Source
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
