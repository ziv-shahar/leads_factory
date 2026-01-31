'use client'

import { LeadReasons } from '@/types/database'
import { TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils/cn'

interface ScoreBreakdownProps {
  reasons: LeadReasons
  totalScore: number
  className?: string
}

export function ScoreBreakdown({ reasons, totalScore, className }: ScoreBreakdownProps) {
  // Extract event types and their scores (exclude evidence_event_ids and total_events)
  const eventScores = Object.entries(reasons)
    .filter(([key]) => key !== 'evidence_event_ids' && key !== 'total_events')
    .map(([eventType, score]) => ({
      eventType,
      score: score as number,
      percentage: totalScore > 0 ? ((score as number) / totalScore) * 100 : 0,
    }))
    .sort((a, b) => b.score - a.score)

  if (eventScores.length === 0) {
    return (
      <div className={cn('text-center py-8', className)}>
        <p className="text-gray-600 dark:text-gray-400 text-sm">No scoring data available</p>
      </div>
    )
  }

  const getScoreColor = (score: number) => {
    if (score >= 20) return 'bg-success-500 dark:bg-success-600'
    if (score >= 15) return 'bg-primary-500 dark:bg-primary-600'
    if (score >= 10) return 'bg-blue-500 dark:bg-blue-600'
    return 'bg-gray-400 dark:bg-gray-600'
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          Score Breakdown
        </h3>
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-gray-500" />
          <span className="text-2xl font-bold text-gray-900 dark:text-white">
            {totalScore}
          </span>
        </div>
      </div>

      {/* Score Bars */}
      <div className="space-y-3">
        {eventScores.map(({ eventType, score, percentage }) => (
          <div key={eventType}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                {eventType.replace(/_/g, ' ')}
              </span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">
                +{score}
              </span>
            </div>
            <div className="relative w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all', getScoreColor(score))}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">Total Event Types</span>
          <span className="font-medium text-gray-900 dark:text-white">
            {eventScores.length}
          </span>
        </div>
        {reasons.total_events && (
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-gray-600 dark:text-gray-400">Total Events</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {reasons.total_events}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
