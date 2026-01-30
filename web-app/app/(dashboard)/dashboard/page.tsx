import { Target, TrendingUp, Users, DollarSign } from 'lucide-react'

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
  const changeColors = {
    positive: 'text-success-600 bg-success-100',
    negative: 'text-danger-600 bg-danger-100',
    neutral: 'text-gray-600 bg-gray-100',
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
            {title}
          </p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
            {value}
          </p>
          <p className="mt-2 flex items-center text-sm">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${changeColors[changeType]}`}
            >
              {change}
            </span>
            <span className="ml-2 text-gray-500 dark:text-gray-400">
              from last month
            </span>
          </p>
        </div>
        <div className="p-3 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
          <Icon className="h-8 w-8 text-primary-600 dark:text-primary-400" />
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Welcome back! Here's an overview of your lead intelligence.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Leads"
          value="1,247"
          change="+12.5%"
          changeType="positive"
          icon={Target}
        />
        <StatCard
          title="New This Week"
          value="84"
          change="+8.2%"
          changeType="positive"
          icon={TrendingUp}
        />
        <StatCard
          title="Daily Limit Used"
          value="23/50"
          change="46%"
          changeType="neutral"
          icon={Users}
        />
        <StatCard
          title="Avg Lead Score"
          value="67"
          change="-2.4%"
          changeType="negative"
          icon={DollarSign}
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
            Top Leads
          </h2>
          <a
            href="/leads"
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            View all
          </a>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Company
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  State
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Last Event
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {[
                { company: 'Acme Corporation', state: 'FL', score: 85, status: 'ACTIVE', event: 'Funding Round' },
                { company: 'Tech Innovations LLC', state: 'CA', score: 78, status: 'ACTIVE', event: 'Hiring Surge' },
                { company: 'Global Solutions Inc', state: 'TX', score: 72, status: 'NEW', event: 'Partnership' },
                { company: 'Future Systems', state: 'NY', score: 68, status: 'ACTIVE', event: 'Expansion' },
                { company: 'Digital Dynamics', state: 'FL', score: 65, status: 'NEW', event: 'Product Launch' },
              ].map((lead, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10 rounded-lg bg-gradient-to-br from-primary-400 to-secondary-500 flex items-center justify-center text-white font-semibold">
                        {lead.company.charAt(0)}
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {lead.company}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs font-medium rounded-md bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
                      {lead.state}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <span className="text-sm font-semibold text-gray-900 dark:text-white">
                        {lead.score}
                      </span>
                      <div className="ml-2 w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-success-500 rounded-full"
                          style={{ width: `${lead.score}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        lead.status === 'ACTIVE'
                          ? 'bg-success-100 text-success-800'
                          : 'bg-primary-100 text-primary-800'
                      }`}
                    >
                      {lead.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {lead.event}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <a
                      href={`/leads/${i + 1}`}
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
      </div>
    </div>
  )
}
