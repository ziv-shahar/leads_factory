'use client'

import { useState, useEffect } from 'react'
import { Target, TrendingUp, Calendar, Building2 } from 'lucide-react'
import type { LeadWithEntity } from '@/types/database'

// Stat Card Component
function StatCard({
  title,
  value,
  change,
  changeType,
  icon: Icon,
}: {
  title: string
  value: string
  change: string
  changeType: 'positive' | 'negative' | 'neutral'
  icon: React.ElementType
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
            {title}
          </p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
            {value}
          </p>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            {change}
          </p>
        </div>
        <div className="p-3 bg-primary-50 dark:bg-primary-900/20 rounded-lg flex-shrink-0">
          <Icon className="h-8 w-8 text-primary-600 dark:text-primary-400" />
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [leads, setLeads] = useState<LeadWithEntity[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    total: 0,
    newThisWeek: 0,
    activeOpportunities: 0,
    businessEvents: 0
  })

  useEffect(() => {
    fetchDashboardData()
  }, [])

  async function fetchDashboardData() {
    try {
      // Fetch top leads
      const leadsResponse = await fetch('/api/location-leads?limit=5&status=NEW,ACTIVE')
      const leadsData = await leadsResponse.json()

      if (leadsResponse.ok) {
        setLeads(leadsData.leads || [])

        // Calculate stats from the full dataset
        const allLeadsResponse = await fetch('/api/location-leads?limit=1000&status=NEW,ACTIVE,CONTACTED,QUALIFIED')
        const allData = await allLeadsResponse.json()

        if (allLeadsResponse.ok) {
          const allLeads = allData.leads || []
          const weekAgo = new Date()
          weekAgo.setDate(weekAgo.getDate() - 7)

          setStats({
            total: allData.total,
            newThisWeek: allLeads.filter((l: LeadWithEntity) =>
              new Date(l.created_at) > weekAgo
            ).length,
            activeOpportunities: allLeads.filter((l: LeadWithEntity) =>
              l.entity.entity_type === 'government_agency'
            ).length,
            businessEvents: allLeads.filter((l: LeadWithEntity) =>
              l.entity.entity_type !== 'government_agency'
            ).length
          })
        }
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Track your lead intelligence and opportunities.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Leads"
          value={stats.total.toString()}
          change="All Types"
          changeType="neutral"
          icon={Target}
        />
        <StatCard
          title="New This Week"
          value={stats.newThisWeek.toString()}
          change="Last 7 days"
          changeType="positive"
          icon={TrendingUp}
        />
        <StatCard
          title="Gov Opportunities"
          value={stats.activeOpportunities.toString()}
          change="Active agencies"
          changeType="neutral"
          icon={Building2}
        />
        <StatCard
          title="Business Events"
          value={stats.businessEvents.toString()}
          change="Expansions, funding, etc"
          changeType="neutral"
          icon={Calendar}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lead Trends Chart */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Lead Trends
            </h2>
            <div className="h-64 flex items-center justify-center text-gray-400">
              {/* Chart placeholder */}
              <div className="text-center">
                <TrendingUp className="h-12 w-12 mx-auto mb-2" />
                <p>Chart will be implemented with Recharts</p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Recent Activity
            </h2>
            <div className="space-y-4">
              {[
                { company: 'Acme Corp', event: 'Funding Round', state: 'FL', time: '2h ago' },
                { company: 'Tech Innovations', event: 'Hiring Surge', state: 'CA', time: '4h ago' },
                { company: 'Global Solutions', event: 'Partnership', state: 'TX', time: '6h ago' },
                { company: 'Future Systems', event: 'Expansion', state: 'NY', time: '8h ago' },
              ].map((item, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-primary-400 to-secondary-500 flex items-center justify-center text-white font-semibold text-sm">
                    {item.company.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {item.company}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {item.event} • {item.state}
                    </p>
                  </div>
                  <span className="text-xs text-gray-400">{item.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Leads Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Recent Leads
          </h2>
          <a
            href="/leads"
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            View all
          </a>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            Loading...
          </div>
        ) : leads.length === 0 ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            No leads found
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead>
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Company
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Location
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Events
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 rounded-lg bg-gradient-to-br from-primary-400 to-secondary-500 flex items-center justify-center text-white font-semibold">
                          {lead.entity.canonical_name.charAt(0)}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {lead.entity.canonical_name}
                          </div>
                          {lead.entity.domain && (
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              {lead.entity.domain}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium rounded-md bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
                        {lead.city ? `${lead.city}, ${lead.state}` : lead.state}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-600 dark:text-gray-300 capitalize">
                        {lead.entity.entity_type?.replace(/_/g, ' ') || 'Company'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          lead.status === 'ACTIVE'
                            ? 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-300'
                            : lead.status === 'NEW'
                            ? 'bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-300'
                            : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                        }`}
                      >
                        {lead.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {lead.event_count} signal{lead.event_count !== 1 ? 's' : ''}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <a
                        href={`/leads/${lead.id}`}
                        className="text-primary-600 dark:text-primary-400 hover:underline"
                      >
                        View
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
