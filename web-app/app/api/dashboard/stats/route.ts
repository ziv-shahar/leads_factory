/**
 * Dashboard Statistics API
 * GET /api/dashboard/stats - Get dashboard metrics
 */

import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'
import type { DashboardStatsResponse } from '@/types/database'
import { formatDistanceToNow } from 'date-fns'

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const states = searchParams.get('states')?.split(',').filter(Boolean) || []

    const supabase = await createClient()

    // Get current user (for daily limit tracking)
    const { data: { user } } = await supabase.auth.getUser()

    // 1. Total active leads
    let totalQuery = supabase
      .from('location_leads')
      .select('*', { count: 'exact', head: true })
      .in('status', ['NEW', 'ACTIVE'])

    if (states.length > 0) {
      totalQuery = totalQuery.in('state', states)
    }

    const { count: totalLeads } = await totalQuery

    // 2. New leads this week
    const oneWeekAgo = new Date()
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)

    let newQuery = supabase
      .from('location_leads')
      .select('*', { count: 'exact', head: true })
      .gte('created_at', oneWeekAgo.toISOString())
      .in('status', ['NEW', 'ACTIVE'])

    if (states.length > 0) {
      newQuery = newQuery.in('state', states)
    }

    const { count: newThisWeek } = await newQuery

    // 3. Average score
    let avgQuery = supabase
      .from('location_leads')
      .select('score')
      .in('status', ['NEW', 'ACTIVE'])

    if (states.length > 0) {
      avgQuery = avgQuery.in('state', states)
    }

    const { data: scoreData } = await avgQuery
    const avgScore =
      scoreData && scoreData.length > 0
        ? Math.round(
            scoreData.reduce((sum, l) => sum + l.score, 0) / scoreData.length
          )
        : 0

    // 4. Daily limit usage (for current user)
    let dailyLimitUsed = 0
    let dailyLimitMax = 50 // Default, will be updated from user permissions

    if (user) {
      const today = new Date().toISOString().split('T')[0]

      const { data: usageData } = await supabase
        .from('lead_access_log')
        .select('id', { count: 'exact', head: true })
        .eq('user_id', user.id)
        .gte('accessed_at', `${today}T00:00:00`)
        .lte('accessed_at', `${today}T23:59:59`)

      dailyLimitUsed = usageData?.length || 0

      // Get user's daily limit from permissions
      const { data: userPerms } = await supabase
        .from('user_permissions')
        .select(`
          max_daily_leads,
          role:roles (
            permissions
          )
        `)
        .eq('user_id', (await supabase
          .from('users')
          .select('id')
          .eq('auth_user_id', user.id)
          .single()
        ).data?.id || '')
        .single()

      if (userPerms) {
        const roleMaxDaily = userPerms.role?.permissions?.max_daily_leads
        dailyLimitMax =
          userPerms.max_daily_leads !== null
            ? userPerms.max_daily_leads
            : roleMaxDaily || 50

        // -1 means unlimited
        if (dailyLimitMax === -1) {
          dailyLimitMax = 999999
        }
      }
    }

    // 5. State breakdown (top 10 states by lead count)
    const { data: allLeads } = await supabase
      .from('location_leads')
      .select('state, score')
      .in('status', ['NEW', 'ACTIVE'])

    const stateStatsMap = (allLeads || []).reduce((acc, lead) => {
      if (!acc[lead.state]) {
        acc[lead.state] = { count: 0, totalScore: 0 }
      }
      acc[lead.state].count++
      acc[lead.state].totalScore += lead.score
      return acc
    }, {} as Record<string, { count: number; totalScore: number }>)

    const stateBreakdown = Object.entries(stateStatsMap)
      .map(([state, stats]) => ({
        state,
        count: stats.count,
        avgScore: Math.round(stats.totalScore / stats.count),
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10)

    // 6. Recent activity (last 5 updates)
    const { data: recentLeads } = await supabase
      .from('location_leads')
      .select(`
        state,
        score,
        last_updated_at,
        entity:entities (
          canonical_name
        )
      `)
      .in('status', ['NEW', 'ACTIVE'])
      .order('last_updated_at', { ascending: false })
      .limit(5)

    const recentActivity = (recentLeads || []).map((lead: any) => ({
      entity_name: lead.entity?.canonical_name || 'Unknown',
      event_type: 'Updated', // Could be enhanced to show actual event type
      state: lead.state,
      time_ago: lead.last_updated_at
        ? formatDistanceToNow(new Date(lead.last_updated_at), {
            addSuffix: true,
          })
        : 'Unknown',
      score: lead.score,
    }))

    const response: DashboardStatsResponse = {
      totalLeads: totalLeads || 0,
      newThisWeek: newThisWeek || 0,
      avgScore,
      dailyLimitUsed,
      dailyLimitMax,
      stateBreakdown,
      recentActivity,
    }

    return NextResponse.json(response)
  } catch (error: any) {
    console.error('Unexpected error in dashboard stats API:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
