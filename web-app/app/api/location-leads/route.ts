/**
 * Location Leads API
 * GET /api/location-leads - List leads with filters
 */

import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'
import type { LeadsListResponse } from '@/types/database'

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

    const response: LeadsListResponse = {
      leads: data || [],
      total: count || 0,
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
