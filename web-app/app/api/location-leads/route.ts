/**
 * Location Leads API
 * GET /api/location-leads - List leads with filters
 */

import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'
import type { LeadsListResponse } from '@/types/database'

// Force dynamic rendering for this API route
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)

    // Parse filters from query params
    const states = searchParams.get('states')?.split(',').filter(Boolean) || []
    const statusParam = searchParams.get('status')?.split(',').filter(Boolean) || ['NEW', 'ACTIVE']
    const minScore = parseInt(searchParams.get('minScore') || '0')
    const maxScore = parseInt(searchParams.get('maxScore') || '999')
    const search = searchParams.get('search') || ''
    const limit = Math.min(parseInt(searchParams.get('limit') || '50'), 100)
    const offset = parseInt(searchParams.get('offset') || '0')

    const supabase = await createClient()

    // Build query with entity join
    let query = supabase
      .from('location_leads')
      .select(`
        *,
        entity:entities (
          id,
          canonical_name,
          normalized_name,
          domain,
          entity_type,
          entity_metadata,
          last_enriched_at,
          created_at
        )
      `, { count: 'exact' })
      .in('status', statusParam)
      .gte('score', minScore)
      .lte('score', maxScore)

    // Apply state filter if provided
    if (states.length > 0) {
      query = query.in('state', states)
    }

    // Apply search filter on entity name if provided
    if (search) {
      query = query.ilike('entity.canonical_name', `%${search}%`)
    }

    // Order and paginate
    query = query
      .order('score', { ascending: false })
      .range(offset, offset + limit - 1)

    const { data, error, count } = await query

    if (error) {
      console.error('Error fetching location leads:', error)
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    // For government agencies, fetch the latest event to get opportunity data
    const leadsWithEventData = await Promise.all(
      (data || []).map(async (lead) => {
        // Only fetch events for government agencies
        if (lead.entity?.entity_type === 'government_agency') {
          try {
            // Fetch all events for this entity to filter by state
            const { data: allEvents, error: eventError } = await supabase
              .from('events')
              .select('*')
              .eq('entity_id', lead.entity_id)
              .order('event_time', { ascending: false, nullsFirst: false })
              .order('ingest_time', { ascending: false })

            if (eventError) {
              console.error(`Error fetching events for lead ${lead.id}, entity ${lead.entity_id}:`, eventError)
              return lead
            }

            // Prioritize events matching this lead's state
            // NOTE: Location leads are created based on strict.key_facts.state
            // (see src/scoring/location_lead_scorer.py line 91)
            const events = (allEvents || []).sort((a, b) => {
              const aState = a.strict?.key_facts?.state
              const bState = b.strict?.key_facts?.state

              const aMatchesState = aState === lead.state ? 1 : 0
              const bMatchesState = bState === lead.state ? 1 : 0

              // Events matching the state come first
              if (aMatchesState !== bMatchesState) {
                return bMatchesState - aMatchesState
              }

              // Then sort by event time
              const aTime = a.event_time ? new Date(a.event_time).getTime() : 0
              const bTime = b.event_time ? new Date(b.event_time).getTime() : 0
              return bTime - aTime
            })

            const latestEvent = events[0] || null

            if (latestEvent) {
              console.log(`Found event for lead ${lead.id} (${lead.state}):`, {
                event_id: latestEvent.id,
                event_state: latestEvent.strict?.key_facts?.state,
                matches_state: latestEvent.strict?.key_facts?.state === lead.state,
                has_key_facts: !!latestEvent.strict?.key_facts,
                key_facts_type: Array.isArray(latestEvent.strict?.key_facts) ? 'array' : typeof latestEvent.strict?.key_facts
              })
            } else {
              console.log(`No events found for lead ${lead.id}, entity ${lead.entity_id}`)
            }

            return {
              ...lead,
              latest_event: latestEvent
            }
          } catch (err) {
            console.error(`Error fetching events for lead ${lead.id}:`, err)
            return lead
          }
        }
        return lead
      })
    )

    // Filter out expired government opportunities (deadline passed or missing)
    const filteredLeads = leadsWithEventData.filter(lead => {
      // Only filter government agencies
      if (lead.entity?.entity_type !== 'government_agency') {
        return true // Keep non-government leads
      }

      // If no event data, keep the lead
      if (!lead.latest_event) {
        return true
      }

      // Check for response_deadline in key_facts.other
      const keyFacts = lead.latest_event.strict?.key_facts
      if (!keyFacts || typeof keyFacts !== 'object' || Array.isArray(keyFacts)) {
        return true
      }

      const other = keyFacts.other
      if (!other || typeof other !== 'object') {
        return true
      }

      const deadline = other.response_deadline
      if (!deadline) {
        // No deadline = likely expired/closed, filter it out
        return false
      }

      // Check if deadline has passed
      try {
        const deadlineDate = new Date(deadline)
        const now = new Date()

        // Keep only if deadline is in the future
        return deadlineDate >= now
      } catch (e) {
        // If date parsing fails, filter it out (likely bad data)
        return false
      }
    })

    console.log(`Returning ${filteredLeads.length} leads (filtered ${leadsWithEventData.length - filteredLeads.length} expired), ${filteredLeads.filter(l => l.latest_event).length} with events`)

    const response: LeadsListResponse = {
      leads: filteredLeads,
      total: count || 0, // Note: total count is pre-filter, consider recalculating if needed
      limit,
      offset,
    }

    return NextResponse.json(response)
  } catch (error: any) {
    console.error('Unexpected error in location-leads API:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
