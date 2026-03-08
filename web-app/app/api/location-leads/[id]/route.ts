/**
 * Single Location Lead API
 * GET /api/location-leads/:id - Get lead details with events
 */

import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'
import type { LeadDetailResponse } from '@/types/database'

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const supabase = await createClient()

    // Get lead with entity details
    const { data: lead, error: leadError } = await supabase
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
      `)
      .eq('id', params.id)
      .single()

    if (leadError) {
      console.error('Error fetching lead:', leadError)
      return NextResponse.json(
        { error: leadError.message },
        { status: leadError.code === 'PGRST116' ? 404 : 500 }
      )
    }

    if (!lead) {
      return NextResponse.json(
        { error: 'Lead not found' },
        { status: 404 }
      )
    }

    // Get all events for this entity
    const { data: allEvents, error: eventsError } = await supabase
      .from('events')
      .select('*')
      .eq('entity_id', lead.entity_id)
      .order('event_time', { ascending: false, nullsFirst: false })
      .order('ingest_time', { ascending: false })

    if (eventsError) {
      console.error('Error fetching events:', eventsError)
      // Don't fail the whole request if events fail
    }

    // Filter events to only show those matching this lead's state
    // NOTE: For government agencies, filter by key_facts.state
    // For companies, show all events (they use different location fields)
    const isGovernmentAgency = lead.entity?.entity_type === 'government_agency'

    const events = (allEvents || []).filter(event => {
      if (isGovernmentAgency) {
        // For government opportunities: match key_facts.state
        const eventState = event.strict?.key_facts?.state
        return eventState === lead.state
      } else {
        // For companies: show all events (no state filtering)
        return true
      }
    }).sort((a, b) => {
      // Sort by event time (most recent first)
      const aTime = a.event_time ? new Date(a.event_time).getTime() : 0
      const bTime = b.event_time ? new Date(b.event_time).getTime() : 0
      return bTime - aTime
    })

    const response: LeadDetailResponse = {
      lead,
      events,
    }

    return NextResponse.json(response)
  } catch (error: any) {
    console.error('Unexpected error in lead detail API:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
