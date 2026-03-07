'use client'

import { LeadWithEntity } from '@/types/database'
import { Building2, MapPin, Calendar, FileText, DollarSign, Ruler, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils/cn'
import Link from 'next/link'
import {
  formatDeadlineWithCountdown,
  getDeadlineUrgency,
  getOpportunityStatusColor,
  getUrgencyColor,
  formatSquareFootage,
  formatBudget,
  mapOpportunityStatus,
  type OpportunityData
} from '@/lib/utils/opportunity'

interface GovernmentOpportunityCardProps {
  lead: LeadWithEntity
  opportunityData?: OpportunityData
  className?: string
}

export function GovernmentOpportunityCard({ lead, opportunityData, className }: GovernmentOpportunityCardProps) {
  const { entity } = lead

  // Extract opportunity details
  const deadline = opportunityData?.response_deadline
  const status = opportunityData?.opportunity_status || opportunityData?.temporal_status || 'active'
  const solicitation = opportunityData?.solicitation_number
  const size = formatSquareFootage(opportunityData?.aboa_sf_min, opportunityData?.aboa_sf_max)
  const budget = formatBudget(opportunityData?.amount)
  const location = opportunityData?.delineated_area || (lead.city ? `${lead.city}, ${lead.state}` : lead.state)

  // Calculate deadline info
  const deadlineInfo = deadline ? formatDeadlineWithCountdown(deadline) : null
  const urgency = deadline ? getDeadlineUrgency(deadline) : 'normal'

  // Show urgent border if deadline is within 7 days
  const isUrgent = urgency === 'urgent'
  const isExpired = urgency === 'expired'

  return (
    <Link href={`/leads/${lead.id}`} className="block h-full">
      <div
        className={cn(
          'h-full bg-white dark:bg-gray-800 rounded-xl border-2',
          isUrgent && 'border-red-300 dark:border-red-700 shadow-lg shadow-red-100 dark:shadow-red-900/30',
          !isUrgent && 'border-gray-100 dark:border-gray-700',
          'hover:border-primary-400 dark:hover:border-primary-500 hover:shadow-2xl',
          'transition-all duration-300 cursor-pointer group',
          'flex flex-col',
          className
        )}
      >
        {/* Header with Agency Name and Status */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 px-6 py-4 rounded-t-xl border-b-2 border-blue-100 dark:border-blue-800">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              {/* Government Icon */}
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white flex-shrink-0 group-hover:scale-110 transition-all duration-300 shadow-md">
                <Building2 className="h-6 w-6" />
              </div>

              {/* Agency Name */}
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-gray-900 dark:text-white text-lg mb-0.5 truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                  {entity.canonical_name}
                </h3>
                {entity.domain && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {entity.domain}
                  </p>
                )}
              </div>
            </div>

            {/* Status Badge */}
            <div className={cn(
              'inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide border flex-shrink-0',
              getOpportunityStatusColor(status)
            )}>
              {mapOpportunityStatus(status)}
            </div>
          </div>

          {/* Solicitation Number */}
          {solicitation && (
            <div className="mt-3 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
              <FileText className="h-4 w-4" />
              <span className="font-mono font-semibold">{solicitation}</span>
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="px-6 py-5 flex-1 flex flex-col">
          {/* Title/Summary */}
          <div className="mb-5">
            <p className="text-base font-semibold text-gray-700 dark:text-gray-200 line-clamp-2">
              {opportunityData?.notice_type || 'Office Space Lease Opportunity'}
            </p>
          </div>

          {/* 3-Column Metrics */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            {/* Deadline */}
            <div className="flex flex-col items-center text-center p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50">
              <Calendar className={cn(
                "h-5 w-5 mb-2",
                isUrgent && "text-red-600 dark:text-red-400",
                urgency === 'warning' && "text-amber-600 dark:text-amber-400",
                urgency === 'normal' && "text-blue-600 dark:text-blue-400",
                isExpired && "text-gray-400 dark:text-gray-500"
              )} />
              <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mb-1">DEADLINE</p>
              {deadlineInfo ? (
                <>
                  <p className="text-sm font-bold text-gray-900 dark:text-white leading-tight">
                    {deadlineInfo.formatted}
                  </p>
                  <p className={cn(
                    "text-xs font-semibold mt-1",
                    isUrgent && "text-red-600 dark:text-red-400",
                    urgency === 'warning' && "text-amber-600 dark:text-amber-400",
                    urgency === 'normal' && "text-blue-600 dark:text-blue-400",
                    isExpired && "text-gray-400"
                  )}>
                    ({deadlineInfo.countdown})
                  </p>
                </>
              ) : (
                <p className="text-sm font-bold text-gray-400 dark:text-gray-500">TBD</p>
              )}
            </div>

            {/* Size */}
            <div className="flex flex-col items-center text-center p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50">
              <Ruler className="h-5 w-5 mb-2 text-purple-600 dark:text-purple-400" />
              <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mb-1">SIZE</p>
              <p className="text-sm font-bold text-gray-900 dark:text-white leading-tight">
                {size}
              </p>
            </div>

            {/* Budget */}
            <div className="flex flex-col items-center text-center p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50">
              <DollarSign className="h-5 w-5 mb-2 text-green-600 dark:text-green-400" />
              <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mb-1">BUDGET</p>
              <p className="text-sm font-bold text-gray-900 dark:text-white leading-tight">
                {budget}
              </p>
            </div>
          </div>

          {/* Secondary Info */}
          <div className="space-y-2 mb-4">
            {/* Location */}
            <div className="flex items-center gap-2 text-sm">
              <MapPin className="h-4 w-4 text-gray-400 flex-shrink-0" />
              <span className="text-gray-600 dark:text-gray-300 font-medium truncate">
                {location}
              </span>
            </div>

            {/* Additional Details */}
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
              {opportunityData?.lease_term_years && (
                <span>📋 {opportunityData.lease_term_years} yr lease{opportunityData.firm_term_years ? ` (${opportunityData.firm_term_years} firm)` : ''}</span>
              )}
              {opportunityData?.parking_spaces && (
                <span>🚗 {opportunityData.parking_spaces} spaces</span>
              )}
              {opportunityData?.facility_security_level && (
                <span>🔒 Level {opportunityData.facility_security_level}</span>
              )}
            </div>
          </div>

          {/* Urgency Warning */}
          {isUrgent && !isExpired && (
            <div className="mt-auto mb-4">
              <div className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg',
                getUrgencyColor('urgent')
              )}>
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span className="text-xs font-bold">
                  CLOSING SOON - {deadlineInfo?.countdown.toUpperCase()}
                </span>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="mt-auto pt-4 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>
              {lead.event_count} event{lead.event_count !== 1 ? 's' : ''}
            </span>
            <span className="font-semibold text-primary-600 dark:text-primary-400 group-hover:underline">
              View Details →
            </span>
          </div>
        </div>
      </div>
    </Link>
  )
}
