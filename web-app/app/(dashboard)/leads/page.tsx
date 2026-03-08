'use client'

import { useState, useEffect } from 'react'
import { StateFilter } from '@/components/leads/state-filter'
import { LeadCardRouter } from '@/components/leads/lead-card-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Search, Download, Filter, Loader2 } from 'lucide-react'
import type { LeadWithEntity, LeadStatus, Event } from '@/types/database'
import type { OpportunityData } from '@/lib/utils/opportunity'

// Helper to extract opportunity data from event
type KeyFactsObject = {
  aboa_sf_min?: number
  aboa_sf_max?: number
  amount?: string
  other?: {
    solicitation_number?: string
    response_deadline?: string
    opportunity_status?: string
    notice_type?: string
    delineated_area?: string
    lease_term_years?: number
    firm_term_years?: number
    parking_spaces?: number
    facility_security_level?: string
    sub_agency?: string
  }
}

const isKeyFactsObject = (kf: any): kf is KeyFactsObject =>
  kf != null && typeof kf === 'object' && !Array.isArray(kf)

function extractOpportunityData(event: Event | null | undefined): OpportunityData | undefined {
  if (!event?.strict?.key_facts) return undefined

  const keyFacts = event.strict.key_facts
  if (!isKeyFactsObject(keyFacts)) return undefined

  return {
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
  }
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadWithEntity[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)

  // Filters
  const [selectedStates, setSelectedStates] = useState<string[]>([])
  const [selectedStatus, setSelectedStatus] = useState<LeadStatus[]>(['NEW', 'ACTIVE'])
  const [searchQuery, setSearchQuery] = useState('')

  // Pagination
  const [page, setPage] = useState(1)
  const [limit] = useState(24)

  // Fetch leads
  useEffect(() => {
    fetchLeads()
  }, [selectedStates, selectedStatus, searchQuery, page])

  async function fetchLeads() {
    setLoading(true)
    try {
      const params = new URLSearchParams()

      if (selectedStates.length > 0) {
        params.set('states', selectedStates.join(','))
      }
      if (selectedStatus.length > 0) {
        params.set('status', selectedStatus.join(','))
      }
      if (searchQuery) {
        params.set('search', searchQuery)
      }
      params.set('limit', limit.toString())
      params.set('offset', ((page - 1) * limit).toString())

      const response = await fetch(`/api/location-leads?${params}`)
      const data = await response.json()

      if (response.ok) {
        setLeads(data.leads)
        setTotal(data.total)
      } else {
        console.error('Error fetching leads:', data.error)
      }
    } catch (error) {
      console.error('Error fetching leads:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    // TODO: Implement export functionality
    console.log('Export leads')
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-6 border-b-2 border-gray-100 dark:border-gray-800">
        <div>
          <h1 className="text-4xl font-black text-gray-900 dark:text-white mb-2">
            Lead Intelligence
          </h1>
          <p className="text-base text-gray-600 dark:text-gray-400">
            {total > 0 ? (
              <>
                <span className="font-bold text-primary-600 dark:text-primary-400">{total}</span> qualified leads discovered
                {selectedStates.length > 0 && <> in <span className="font-semibold">{selectedStates.length} state{selectedStates.length !== 1 ? 's' : ''}</span></>}
              </>
            ) : (
              'No leads found matching your criteria'
            )}
          </p>
        </div>

        <Button onClick={handleExport} variant="outline" className="gap-2 px-6">
          <Download className="h-4 w-4" />
          Export Data
        </Button>
      </div>

      {/* Filters */}
      <div className="bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 rounded-xl border-2 border-gray-100 dark:border-gray-700 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="h-5 w-5 text-primary-600 dark:text-primary-400" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Filters</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              type="text"
              placeholder="Search companies..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* State Filter */}
          <StateFilter
            selected={selectedStates}
            onChange={setSelectedStates}
          />

          {/* Status Filter */}
          <div>
            <select
              value={selectedStatus.join(',')}
              onChange={e => {
                const values = e.target.value.split(',').filter(Boolean) as LeadStatus[]
                setSelectedStatus(values.length > 0 ? values : ['NEW', 'ACTIVE'])
              }}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
            >
              <option value="NEW,ACTIVE">Active & New</option>
              <option value="NEW">New Only</option>
              <option value="ACTIVE">Active Only</option>
              <option value="CONTACTED">Contacted</option>
              <option value="QUALIFIED">Qualified</option>
              <option value="NEW,ACTIVE,CONTACTED,QUALIFIED">All Statuses</option>
            </select>
          </div>
        </div>

        {/* Active Filters Summary */}
        {(selectedStates.length > 0 || searchQuery) && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Active filters:
            </span>

            {selectedStates.length > 0 && (
              <span className="inline-flex items-center px-2 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-md text-xs font-medium">
                {selectedStates.length} state{selectedStates.length !== 1 ? 's' : ''}
              </span>
            )}

            {searchQuery && (
              <span className="inline-flex items-center px-2 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-md text-xs font-medium">
                Search: "{searchQuery}"
              </span>
            )}

            <button
              onClick={() => {
                setSelectedStates([])
                setSearchQuery('')
              }}
              className="text-xs text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 underline"
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        </div>
      )}

      {/* Empty State */}
      {!loading && leads.length === 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
          <Filter className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            No leads found
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Try adjusting your filters to see more results
          </p>
          <Button
            onClick={() => {
              setSelectedStates([])
              setSearchQuery('')
            }}
            variant="outline"
          >
            Clear filters
          </Button>
        </div>
      )}

      {/* Leads Grid */}
      {!loading && leads.length > 0 && (
        <>
          {/* Results Summary */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Showing <span className="font-semibold text-gray-900 dark:text-white">{leads.length}</span> of <span className="font-semibold text-gray-900 dark:text-white">{total}</span> leads
            </p>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Page {page} of {totalPages}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {leads.map(lead => {
              // Extract opportunity data from latest_event for government opportunities
              const opportunityData = lead.entity.entity_type === 'government_agency'
                ? extractOpportunityData(lead.latest_event)
                : undefined

              return (
                <LeadCardRouter
                  key={lead.id}
                  lead={lead}
                  opportunityData={opportunityData}
                />
              )
            })}
          </div>
        </>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            variant="outline"
            size="sm"
          >
            Previous
          </Button>

          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
              let pageNum
              if (totalPages <= 7) {
                pageNum = i + 1
              } else if (page <= 4) {
                pageNum = i + 1
              } else if (page >= totalPages - 3) {
                pageNum = totalPages - 6 + i
              } else {
                pageNum = page - 3 + i
              }

              return (
                <Button
                  key={i}
                  onClick={() => setPage(pageNum)}
                  variant={page === pageNum ? 'default' : 'ghost'}
                  size="sm"
                  className="w-8 h-8 p-0"
                >
                  {pageNum}
                </Button>
              )
            })}
          </div>

          <Button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            variant="outline"
            size="sm"
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
