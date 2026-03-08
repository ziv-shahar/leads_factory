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

          {/* Deadline - Prominent Display */}
          {deadlineInfo && (
            <div className={cn(
              "flex items-center gap-3 p-4 rounded-lg mb-4 border-2",
              isUrgent && "bg-gradient-to-r from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20 border-red-300 dark:border-red-700",
              urgency === 'warning' && "bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 border-amber-300 dark:border-amber-700",
              urgency === 'normal' && "bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-700",
              isExpired && "bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-700"
            )}>
              <div className={cn(
                "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm",
                isUrgent && "bg-red-500 dark:bg-red-600",
                urgency === 'warning' && "bg-amber-500 dark:bg-amber-600",
                urgency === 'normal' && "bg-blue-500 dark:bg-blue-600",
                isExpired && "bg-gray-400 dark:bg-gray-600"
              )}>
                <Calendar className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1">
                <p className={cn(
                  "text-xs font-semibold uppercase tracking-wide mb-0.5",
                  isUrgent && "text-red-600 dark:text-red-400",
                  urgency === 'warning' && "text-amber-600 dark:text-amber-400",
                  urgency === 'normal' && "text-blue-600 dark:text-blue-400",
                  isExpired && "text-gray-500 dark:text-gray-400"
                )}>
                  Response Deadline
                </p>
                <div className="flex items-baseline gap-2">
                  <p className="text-base font-bold text-gray-900 dark:text-white">
                    {deadlineInfo.formatted}
                  </p>
                  <p className={cn(
                    "text-sm font-bold",
                    isUrgent && "text-red-600 dark:text-red-400",
                    urgency === 'warning' && "text-amber-600 dark:text-amber-400",
                    urgency === 'normal' && "text-blue-600 dark:text-blue-400",
                    isExpired && "text-gray-500 dark:text-gray-400"
                  )}>
                    ({deadlineInfo.countdown})
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Optional Metrics - Only show if not TBD */}
          {(size !== 'TBD' || budget !== 'TBD') && (
            <div className="flex gap-3 mb-4">
              {size !== 'TBD' && (
                <div className="flex-1 flex items-center gap-2 p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800/30">
                  <Ruler className="h-4 w-4 text-purple-600 dark:text-purple-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs text-purple-600 dark:text-purple-400 font-semibold">Size</p>
                    <p className="text-sm font-bold text-gray-900 dark:text-white truncate">
                      {size}
                    </p>
                  </div>
                </div>
              )}
              {budget !== 'TBD' && (
                <div className="flex-1 flex items-center gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-800/30">
                  <DollarSign className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs text-green-600 dark:text-green-400 font-semibold">Budget</p>
                    <p className="text-sm font-bold text-gray-900 dark:text-white truncate">
                      {budget}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Location - Prominent Display */}
          <div className="mb-4">
            <div className="flex items-center gap-2 p-3 rounded-lg bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-900/30 dark:to-slate-900/30 border border-gray-200 dark:border-gray-700">
              <MapPin className="h-4 w-4 text-gray-600 dark:text-gray-400 flex-shrink-0" />
              <span className="text-sm text-gray-900 dark:text-white font-semibold truncate">
                {location}
              </span>
            </div>
          </div>

          {/* Additional Details */}
          {(opportunityData?.lease_term_years || opportunityData?.parking_spaces || opportunityData?.facility_security_level) && (
            <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-gray-600 dark:text-gray-300 mb-4">
              {opportunityData?.lease_term_years && (
                <div className="flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-gray-400" />
                  <span>{opportunityData.lease_term_years} yr lease{opportunityData.firm_term_years ? ` (${opportunityData.firm_term_years} firm)` : ''}</span>
                </div>
              )}
              {opportunityData?.parking_spaces && (
                <div className="flex items-center gap-1.5">
                  <Building2 className="h-3.5 w-3.5 text-gray-400" />
                  <span>{opportunityData.parking_spaces} spaces</span>
                </div>
              )}
              {opportunityData?.facility_security_level && (
                <div className="flex items-center gap-1.5">
                  <AlertCircle className="h-3.5 w-3.5 text-gray-400" />
                  <span>Level {opportunityData.facility_security_level}</span>
                </div>
              )}
            </div>
          )}

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
