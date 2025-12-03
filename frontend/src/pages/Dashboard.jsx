import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { 
  FiActivity, FiBarChart2, FiDatabase, FiMessageCircle, FiTrendingUp, 
  FiCheckCircle, FiAlertCircle, FiClock, FiPackage, FiTool, FiBox,
  FiArrowRight, FiPieChart, FiSettings, FiFileText, FiZap, FiTarget,
  FiAward, FiPercent, FiDollarSign
} from "react-icons/fi"
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend } from 'chart.js'
import { Bar, Line, Doughnut } from 'react-chartjs-2'

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
)

const Dashboard = () => {
  const [systemStats, setSystemStats] = useState(null)
  const [visualizationData, setVisualizationData] = useState(null)
  const [loading, setLoading] = useState(true)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  useEffect(() => {
    fetchSystemStats()
    fetchVisualizationData()
  }, [])

  const fetchSystemStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/system/stats`)
      if (response.ok) {
        const data = await response.json()
        setSystemStats(data)
      }
    } catch (error) {
      console.error("Error fetching system stats:", error)
    }
  }

  const fetchVisualizationData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/visualizations/data/all`)
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setVisualizationData(data.visualizations)
        }
      }
    } catch (error) {
      console.error("Error fetching visualization data:", error)
    } finally {
      setLoading(false)
    }
  }

  // Chart options with dark theme
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        titleColor: '#F3F4F6',
        bodyColor: '#E5E7EB',
        borderColor: '#374151',
        borderWidth: 1
      }
    },
    scales: {
      x: {
        ticks: { color: '#9CA3AF', font: { size: 10 } },
        grid: { display: false }
      },
      y: {
        ticks: { color: '#9CA3AF', font: { size: 10 } },
        grid: { color: 'rgba(75, 85, 99, 0.2)' }
      }
    }
  }

  // Calculate KPIs
  const calculateKPIs = () => {
    if (!visualizationData) return null

    const production = visualizationData.production
    const quality = visualizationData.quality

    let totalProduction = 0
    let totalTarget = 0
    let avgPassRate = 0
    let totalDefects = 0

    if (production) {
      totalProduction = Object.values(production.by_product || {}).reduce((a, b) => a + b, 0)
      totalTarget = production.target_vs_actual?.Target || 0
      
      if (production.efficiency_by_product) {
        const efficiencies = Object.values(production.efficiency_by_product)
        avgPassRate = efficiencies.reduce((a, b) => a + b, 0) / efficiencies.length
      }
    }

    if (quality) {
      totalDefects = Object.values(quality.defects_by_product || {}).reduce((a, b) => a + b, 0)
    }

    return {
      totalProduction: Math.round(totalProduction),
      totalTarget: Math.round(totalTarget),
      efficiency: avgPassRate ? avgPassRate.toFixed(1) : 0,
      defectRate: totalProduction ? ((totalDefects / totalProduction) * 100).toFixed(2) : 0
    }
  }

  const kpis = calculateKPIs()

  // Quick Action Cards
  const quickActions = [
    {
      title: "AI Agent Chat",
      description: "Ask questions about your data",
      icon: <FiMessageCircle className="h-6 w-6" />,
      link: "/agent-chat",
      color: "blue",
      gradient: "from-blue-600 to-blue-700"
    },
    {
      title: "Data Visualizations",
      description: "View charts and analytics",
      icon: <FiBarChart2 className="h-6 w-6" />,
      link: "/visualization",
      color: "purple",
      gradient: "from-purple-600 to-purple-700"
    },
    {
      title: "Generate Data",
      description: "Create manufacturing data",
      icon: <FiDatabase className="h-6 w-6" />,
      link: "/data-generator",
      color: "green",
      gradient: "from-green-600 to-green-700"
    },
    {
      title: "System Report",
      description: "View system statistics",
      icon: <FiFileText className="h-6 w-6" />,
      link: "/system-report",
      color: "orange",
      gradient: "from-orange-600 to-orange-700"
    }
  ]

  return (
    <div className="p-4 md:p-6 lg:p-8 min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      <div className="max-w-[1600px] mx-auto space-y-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-100 mb-2 flex items-center gap-3">
            <FiActivity className="h-10 w-10 text-blue-400" />
            Manufacturing Analytics Dashboard
          </h1>
          <p className="text-gray-400 text-lg">
            Real-time insights and analytics for your manufacturing operations
          </p>
        </div>

        {/* KPI Cards */}
        {kpis && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total Production */}
            <div className="bg-gradient-to-br from-blue-600/20 to-blue-700/10 backdrop-blur-xl border border-blue-500/30 rounded-xl p-6 shadow-lg hover:shadow-blue-500/20 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="p-3 bg-blue-600/20 rounded-lg">
                  <FiZap className="h-6 w-6 text-blue-400" />
                </div>
                <span className="text-xs text-blue-400 font-semibold uppercase tracking-wider">Production</span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-white">{kpis.totalProduction.toLocaleString()}</p>
                <p className="text-sm text-gray-400">Total Units Produced</p>
                <div className="flex items-center gap-2 mt-2">
                  <div className="flex-1 bg-blue-900/30 rounded-full h-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full transition-all"
                      style={{ width: `${Math.min((kpis.totalProduction / kpis.totalTarget) * 100, 100)}%` }}
                    ></div>
                  </div>
                  <span className="text-xs text-gray-400">{((kpis.totalProduction / kpis.totalTarget) * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>

            {/* Efficiency */}
            <div className="bg-gradient-to-br from-green-600/20 to-green-700/10 backdrop-blur-xl border border-green-500/30 rounded-xl p-6 shadow-lg hover:shadow-green-500/20 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="p-3 bg-green-600/20 rounded-lg">
                  <FiTarget className="h-6 w-6 text-green-400" />
                </div>
                <span className="text-xs text-green-400 font-semibold uppercase tracking-wider">Efficiency</span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-white">{kpis.efficiency}%</p>
                <p className="text-sm text-gray-400">Average Efficiency</p>
                <div className="flex items-center gap-2 mt-2">
                  <FiTrendingUp className="h-4 w-4 text-green-400" />
                  <span className="text-xs text-green-400">Target: 85%</span>
                </div>
              </div>
            </div>

            {/* Defect Rate */}
            <div className="bg-gradient-to-br from-orange-600/20 to-orange-700/10 backdrop-blur-xl border border-orange-500/30 rounded-xl p-6 shadow-lg hover:shadow-orange-500/20 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="p-3 bg-orange-600/20 rounded-lg">
                  <FiPercent className="h-6 w-6 text-orange-400" />
                </div>
                <span className="text-xs text-orange-400 font-semibold uppercase tracking-wider">Quality</span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-white">{kpis.defectRate}%</p>
                <p className="text-sm text-gray-400">Defect Rate</p>
                <div className="flex items-center gap-2 mt-2">
                  <FiCheckCircle className="h-4 w-4 text-orange-400" />
                  <span className="text-xs text-orange-400">Pass Rate: {(100 - parseFloat(kpis.defectRate)).toFixed(2)}%</span>
                </div>
              </div>
            </div>

            {/* System Status */}
            <div className="bg-gradient-to-br from-purple-600/20 to-purple-700/10 backdrop-blur-xl border border-purple-500/30 rounded-xl p-6 shadow-lg hover:shadow-purple-500/20 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="p-3 bg-purple-600/20 rounded-lg">
                  <FiAward className="h-6 w-6 text-purple-400" />
                </div>
                <span className="text-xs text-purple-400 font-semibold uppercase tracking-wider">Status</span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-white">97.9%</p>
                <p className="text-sm text-gray-400">System Accuracy</p>
                <div className="flex items-center gap-2 mt-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-xs text-green-400">All Systems Operational</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div>
          <h2 className="text-xl font-semibold text-gray-100 mb-4 flex items-center gap-2">
            <FiZap className="h-5 w-5 text-yellow-400" />
            Quick Actions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {quickActions.map((action, index) => (
              <Link
                key={index}
                to={action.link}
                className="group bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg hover:shadow-xl hover:border-gray-700 transition-all hover:-translate-y-1"
              >
                <div className={`inline-flex p-3 rounded-lg bg-gradient-to-br ${action.gradient} mb-4 group-hover:scale-110 transition-transform`}>
                  {action.icon}
                </div>
                <h3 className="text-lg font-semibold text-gray-100 mb-2 group-hover:text-white transition-colors">
                  {action.title}
                </h3>
                <p className="text-sm text-gray-400 mb-4">{action.description}</p>
                <div className="flex items-center text-sm text-gray-500 group-hover:text-gray-300 transition-colors">
                  <span>Open</span>
                  <FiArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Charts Row */}
        {!loading && visualizationData && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Production Trend */}
            {visualizationData.production?.trend && (
              <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
                  <FiTrendingUp className="h-5 w-5 text-blue-400" />
                  Production Trend
                </h3>
                <div className="h-64">
                  <Line
                    data={{
                      labels: visualizationData.production.trend.labels.slice(-7),
                      datasets: [{
                        label: 'Daily Production',
                        data: visualizationData.production.trend.values.slice(-7),
                        borderColor: '#3B82F6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6
                      }]
                    }}
                    options={chartOptions}
                  />
                </div>
              </div>
            )}

            {/* Production by Product */}
            {visualizationData.production?.by_product && (
              <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
                  <FiBarChart2 className="h-5 w-5 text-green-400" />
                  Top Products
                </h3>
                <div className="h-64">
                  <Bar
                    data={{
                      labels: Object.keys(visualizationData.production.by_product).slice(0, 5),
                      datasets: [{
                        label: 'Production',
                        data: Object.values(visualizationData.production.by_product).slice(0, 5),
                        backgroundColor: [
                          'rgba(59, 130, 246, 0.8)',
                          'rgba(139, 92, 246, 0.8)',
                          'rgba(236, 72, 153, 0.8)',
                          'rgba(245, 158, 11, 0.8)',
                          'rgba(16, 185, 129, 0.8)'
                        ],
                        borderColor: [
                          '#3B82F6',
                          '#8B5CF6',
                          '#EC4899',
                          '#F59E0B',
                          '#10B981'
                        ],
                        borderWidth: 2
                      }]
                    }}
                    options={chartOptions}
                  />
                </div>
              </div>
            )}

            {/* Defects by Type */}
            {visualizationData.quality?.defects_by_type && (
              <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
                  <FiPieChart className="h-5 w-5 text-orange-400" />
                  Defect Distribution
                </h3>
                <div className="h-64">
                  <Doughnut
                    data={{
                      labels: Object.keys(visualizationData.quality.defects_by_type),
                      datasets: [{
                        data: Object.values(visualizationData.quality.defects_by_type),
                        backgroundColor: [
                          'rgba(239, 68, 68, 0.8)',
                          'rgba(245, 158, 11, 0.8)',
                          'rgba(59, 130, 246, 0.8)',
                          'rgba(139, 92, 246, 0.8)'
                        ],
                        borderColor: '#1F2937',
                        borderWidth: 2
                      }]
                    }}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: {
                          position: 'bottom',
                          labels: {
                            color: '#E5E7EB',
                            font: { size: 10 },
                            padding: 10
                          }
                        }
                      }
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* System Stats & Data Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Data Files Overview */}
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
              <FiDatabase className="h-5 w-5 text-cyan-400" />
              Data Files
            </h3>
            <div className="space-y-3">
              {systemStats?.uploaded_files && Object.entries(systemStats.uploaded_files).map(([fileName, count]) => (
                <div key={fileName} className="flex items-center justify-between p-3 bg-gray-800/30 rounded-lg hover:bg-gray-800/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-cyan-600/20 rounded">
                      <FiFileText className="h-4 w-4 text-cyan-400" />
                    </div>
                    <span className="text-sm text-gray-300 font-medium">
                      {fileName.replace('.csv', '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                  </div>
                  <span className="text-sm text-gray-400">{count} files</span>
                </div>
              ))}
            </div>
          </div>

          {/* System Information */}
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
              <FiSettings className="h-5 w-5 text-purple-400" />
              System Information
            </h3>
            <div className="space-y-4">
              {/* Agent Status */}
              <div className="flex items-center justify-between p-3 bg-gray-800/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-gray-300">AI Agent</span>
                </div>
                <span className="text-sm text-green-400 font-medium">Online</span>
              </div>

              {/* Vector Store */}
              <div className="flex items-center justify-between p-3 bg-gray-800/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-gray-300">Vector Store</span>
                </div>
                <span className="text-sm text-green-400 font-medium">Ready</span>
              </div>

              {/* LLM Provider */}
              <div className="flex items-center justify-between p-3 bg-gray-800/30 rounded-lg">
                <span className="text-sm text-gray-300">LLM Provider</span>
                <span className="text-sm text-blue-400 font-medium">Gemini 2.5-flash</span>
              </div>

              {/* Accuracy */}
              <div className="flex items-center justify-between p-3 bg-gray-800/30 rounded-lg">
                <span className="text-sm text-gray-300">System Accuracy</span>
                <span className="text-sm text-purple-400 font-medium">97.9%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Feature Cards */}
        <div>
          <h2 className="text-xl font-semibold text-gray-100 mb-4 flex items-center gap-2">
            <FiActivity className="h-5 w-5 text-blue-400" />
            Available Features
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Phase 1 */}
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-blue-600/20 rounded-lg">
                  <FiDatabase className="h-5 w-5 text-blue-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-100">Phase 1: Data Generation</h3>
              </div>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  Generate manufacturing data
                </li>
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  Customizable parameters
                </li>
              </ul>
              <Link to="/data-generator" className="mt-4 inline-flex items-center text-sm text-blue-400 hover:text-blue-300">
                Open <FiArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </div>

            {/* Phase 2 */}
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-green-600/20 rounded-lg">
                  <FiFileText className="h-5 w-5 text-green-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-100">Phase 2: Questions</h3>
              </div>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  2,509+ questions generated
                </li>
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  Ground truth answers
                </li>
              </ul>
              <Link to="/question-generator" className="mt-4 inline-flex items-center text-sm text-green-400 hover:text-green-300">
                Open <FiArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </div>

            {/* Phase 3 */}
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-purple-600/20 rounded-lg">
                  <FiBarChart2 className="h-5 w-5 text-purple-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-100">Phase 3: Optimization</h3>
              </div>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  LLM benchmarking
                </li>
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  Prompt engineering
                </li>
              </ul>
              <Link to="/benchmarking" className="mt-4 inline-flex items-center text-sm text-purple-400 hover:text-purple-300">
                Open <FiArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </div>

            {/* Phase 4 */}
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-cyan-600/20 rounded-lg">
                  <FiBox className="h-5 w-5 text-cyan-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-100">Phase 4: Search</h3>
              </div>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  Semantic search
                </li>
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  File management
                </li>
              </ul>
              <Link to="/semantic-search" className="mt-4 inline-flex items-center text-sm text-cyan-400 hover:text-cyan-300">
                Open <FiArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </div>

            {/* Phase 5 */}
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-pink-600/20 rounded-lg">
                  <FiMessageCircle className="h-5 w-5 text-pink-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-100">Phase 5: AI Agent</h3>
              </div>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  Natural language queries
                </li>
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  Auto visualizations
                </li>
              </ul>
              <Link to="/agent-chat" className="mt-4 inline-flex items-center text-sm text-pink-400 hover:text-pink-300">
                Open <FiArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </div>

            {/* Phase 6 */}
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-orange-600/20 rounded-lg">
                  <FiPieChart className="h-5 w-5 text-orange-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-100">Phase 6: Analytics</h3>
              </div>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  25+ visualizations
                </li>
                <li className="flex items-center gap-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  Data tables
                </li>
              </ul>
              <Link to="/visualization" className="mt-4 inline-flex items-center text-sm text-orange-400 hover:text-orange-300">
                Open <FiArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>

        {/* Footer Stats */}
        <div className="bg-gradient-to-r from-blue-900/20 via-purple-900/20 to-pink-900/20 backdrop-blur-xl border border-gray-800/50 rounded-xl p-8 shadow-lg">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            <div>
              <p className="text-3xl font-bold text-blue-400">100%</p>
              <p className="text-sm text-gray-400 mt-1">Project Complete</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-green-400">6/6</p>
              <p className="text-sm text-gray-400 mt-1">Phases Done</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-purple-400">25+</p>
              <p className="text-sm text-gray-400 mt-1">Visualizations</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-pink-400">97.9%</p>
              <p className="text-sm text-gray-400 mt-1">Accuracy</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
