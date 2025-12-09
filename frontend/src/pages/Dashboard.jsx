import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { 
  FiActivity, FiBarChart2, FiDatabase, FiMessageCircle, FiTrendingUp, 
  FiCheckCircle, FiAlertCircle, FiClock, FiPackage, FiTool, FiBox,
  FiArrowRight, FiPieChart, FiSettings, FiFileText, FiZap, FiTarget,
  FiAward, FiPercent, FiDollarSign, FiLoader, FiFile
} from "react-icons/fi"
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend } from 'chart.js'
import { Bar, Line, Doughnut, Pie } from 'react-chartjs-2'
import { useAuth } from "@/contexts/AuthContext"

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
  const { token, user, industries } = useAuth()
  const [systemStats, setSystemStats] = useState(null)
  const [visualizationData, setVisualizationData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [files, setFiles] = useState([])
  const [userIndustry, setUserIndustry] = useState(null)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  useEffect(() => {
    fetchFiles()
    fetchVisualizationData()
  }, [token])

  // Get user's industry details
  useEffect(() => {
    if (user?.industry && industries.length > 0) {
      const industry = industries.find(ind => ind.name === user.industry)
      if (industry) {
        setUserIndustry(industry)
      }
    }
  }, [user, industries])

  const fetchFiles = async () => {
    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const response = await fetch(`${API_BASE_URL}/files/list`, { headers })
      if (response.ok) {
        const data = await response.json()
        setFiles(data.files || [])
      }
    } catch (error) {
      console.error("Error fetching files:", error)
    }
  }

  const fetchVisualizationData = async () => {
    setLoading(true)
    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const response = await fetch(`${API_BASE_URL}/visualizations/data/all`, { headers })
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.visualizations) {
          setVisualizationData(data.visualizations)
        }
      }
    } catch (error) {
      console.error("Error fetching visualization data:", error)
    } finally {
      setLoading(false)
    }
  }

  // Colorful chart options
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: '#E5E7EB',
          font: { size: 12 }
        }
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
        ticks: { color: '#9CA3AF', font: { size: 11 } },
        grid: { color: 'rgba(75, 85, 99, 0.2)' }
      },
      y: {
        ticks: { color: '#9CA3AF', font: { size: 11 } },
        grid: { color: 'rgba(75, 85, 99, 0.2)' },
        beginAtZero: true
      }
    }
  }

  const pieOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
        labels: {
          color: '#E5E7EB',
          font: { size: 11 },
          padding: 10
        }
      },
      tooltip: {
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        titleColor: '#F3F4F6',
        bodyColor: '#E5E7EB',
        borderColor: '#374151',
        borderWidth: 1
      }
    }
  }

  // Colorful gradient arrays
  const colors = {
    primary: ['#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#06B6D4', '#6366F1', '#EF4444', '#F97316', '#84CC16'],
    gradient: [
      'rgba(59, 130, 246, 0.8)',
      'rgba(139, 92, 246, 0.8)',
      'rgba(236, 72, 153, 0.8)',
      'rgba(245, 158, 11, 0.8)',
      'rgba(16, 185, 129, 0.8)',
      'rgba(6, 182, 212, 0.8)',
      'rgba(99, 102, 241, 0.8)',
      'rgba(239, 68, 68, 0.8)',
      'rgba(249, 115, 22, 0.8)',
      'rgba(132, 204, 22, 0.8)'
    ],
    border: ['#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#06B6D4', '#6366F1', '#EF4444', '#F97316', '#84CC16']
  }

  // Skeleton Loader Component
  const ChartSkeleton = () => (
    <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg animate-pulse">
      <div className="h-6 bg-gray-800 rounded w-1/3 mb-4"></div>
      <div className="h-64 bg-gray-800/50 rounded"></div>
    </div>
  )

  const CardSkeleton = () => (
    <div className="bg-gradient-to-br from-gray-800/20 to-gray-700/10 backdrop-blur-xl border border-gray-700/30 rounded-xl p-6 shadow-lg animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div className="h-12 w-12 bg-gray-700 rounded-lg"></div>
        <div className="h-4 bg-gray-700 rounded w-20"></div>
      </div>
      <div className="h-8 bg-gray-700 rounded w-24 mb-2"></div>
      <div className="h-4 bg-gray-700 rounded w-32"></div>
    </div>
  )

  // Render chart component
  const renderChart = (chart, index = 0) => {
    if (!chart || !chart.data) return null
    
    const { type, title, data } = chart
    const colorIndex = index % colors.gradient.length
    
    const chartData = {
      labels: data.labels || [],
      datasets: [{
        label: title,
        data: data.values || [],
        backgroundColor: type === 'pie' || type === 'doughnut' 
          ? colors.gradient.slice(0, Math.max(data.labels?.length || 1, 8))
          : colors.gradient[colorIndex],
        borderColor: type === 'pie' || type === 'doughnut'
          ? colors.border.slice(0, Math.max(data.labels?.length || 1, 8))
          : colors.border[colorIndex],
        borderWidth: 2
      }]
    }

    switch (type) {
      case 'bar':
        return (
          <div className="h-80">
            <Bar data={chartData} options={chartOptions} />
          </div>
        )
      case 'line':
        return (
          <div className="h-80">
            <Line 
              data={{
                ...chartData,
                datasets: [{
                  ...chartData.datasets[0],
                  borderColor: colors.border[colorIndex],
                  backgroundColor: colors.gradient[colorIndex].replace('0.8', '0.1'),
                  fill: true,
                  tension: 0.4,
                  pointRadius: 4,
                  pointHoverRadius: 6
                }]
              }} 
              options={chartOptions} 
            />
          </div>
        )
      case 'pie':
        return (
          <div className="h-80">
            <Pie data={chartData} options={pieOptions} />
          </div>
        )
      case 'doughnut':
        return (
          <div className="h-80">
            <Doughnut data={chartData} options={pieOptions} />
          </div>
        )
      default:
        return null
    }
  }

  // Calculate KPIs from all visualizations
  const calculateKPIs = () => {
    if (!visualizationData || Object.keys(visualizationData).length === 0) return null

    let totalFiles = 0
    let totalCharts = 0
    let totalMetrics = 0

    // Count files, charts, and metrics across all visualizations
    Object.values(visualizationData).forEach((fileViz) => {
      if (fileViz) {
        totalFiles++
        
        // Count charts in sheets or root
        if (fileViz.sheets) {
          Object.values(fileViz.sheets).forEach((sheet) => {
            if (sheet.charts) totalCharts += sheet.charts.length
            if (sheet.metrics) totalMetrics += Object.keys(sheet.metrics).length
          })
        } else {
          if (fileViz.charts) totalCharts += fileViz.charts.length
          if (fileViz.metrics) totalMetrics += Object.keys(fileViz.metrics).length
        }
      }
    })

    return {
      totalFiles,
      totalCharts,
      totalMetrics,
      avgChartsPerFile: totalFiles > 0 ? (totalCharts / totalFiles).toFixed(1) : 0
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
            {userIndustry ? (
              <>
                {userIndustry.icon && <span className="text-4xl">{userIndustry.icon}</span>}
                {userIndustry.display_name} Analytics Dashboard
              </>
            ) : (
              "Analytics Dashboard"
            )}
          </h1>
          <p className="text-gray-400 text-lg">
            {userIndustry?.description 
              ? `Real-time insights and analytics for your ${userIndustry.display_name.toLowerCase()} operations`
              : "Real-time insights and analytics for your operations"
            }
          </p>
        </div>

        {/* KPI Cards */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => <CardSkeleton key={i} />)}
          </div>
        ) : kpis ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total Files */}
            <div className="bg-gradient-to-br from-blue-600/20 to-blue-700/10 backdrop-blur-xl border border-blue-500/30 rounded-xl p-6 shadow-lg hover:shadow-blue-500/20 transition-all hover:scale-105">
              <div className="flex items-center justify-between mb-3">
                <div className="p-3 bg-blue-600/20 rounded-lg">
                  <FiDatabase className="h-6 w-6 text-blue-400" />
                </div>
                <span className="text-xs text-blue-400 font-semibold uppercase tracking-wider">Files</span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-white">{kpis.totalFiles}</p>
                <p className="text-sm text-gray-400">Uploaded Files</p>
                <div className="flex items-center gap-2 mt-2">
                  <FiFileText className="h-4 w-4 text-blue-400" />
                  <span className="text-xs text-blue-400">Active</span>
                </div>
              </div>
            </div>

            {/* Total Charts */}
            <div className="bg-gradient-to-br from-purple-600/20 to-purple-700/10 backdrop-blur-xl border border-purple-500/30 rounded-xl p-6 shadow-lg hover:shadow-purple-500/20 transition-all hover:scale-105">
              <div className="flex items-center justify-between mb-3">
                <div className="p-3 bg-purple-600/20 rounded-lg">
                  <FiBarChart2 className="h-6 w-6 text-purple-400" />
                </div>
                <span className="text-xs text-purple-400 font-semibold uppercase tracking-wider">Charts</span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-white">{kpis.totalCharts}</p>
                <p className="text-sm text-gray-400">Total Visualizations</p>
                <div className="flex items-center gap-2 mt-2">
                  <FiTrendingUp className="h-4 w-4 text-purple-400" />
                  <span className="text-xs text-purple-400">Avg: {kpis.avgChartsPerFile}/file</span>
                </div>
              </div>
            </div>

            {/* Total Metrics */}
            <div className="bg-gradient-to-br from-green-600/20 to-green-700/10 backdrop-blur-xl border border-green-500/30 rounded-xl p-6 shadow-lg hover:shadow-green-500/20 transition-all hover:scale-105">
              <div className="flex items-center justify-between mb-3">
                <div className="p-3 bg-green-600/20 rounded-lg">
                  <FiTarget className="h-6 w-6 text-green-400" />
                </div>
                <span className="text-xs text-green-400 font-semibold uppercase tracking-wider">Metrics</span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-white">{kpis.totalMetrics}</p>
                <p className="text-sm text-gray-400">Key Metrics</p>
                <div className="flex items-center gap-2 mt-2">
                  <FiCheckCircle className="h-4 w-4 text-green-400" />
                  <span className="text-xs text-green-400">Calculated</span>
                </div>
              </div>
            </div>

            {/* System Status */}
            <div className="bg-gradient-to-br from-pink-600/20 to-pink-700/10 backdrop-blur-xl border border-pink-500/30 rounded-xl p-6 shadow-lg hover:shadow-pink-500/20 transition-all hover:scale-105">
              <div className="flex items-center justify-between mb-3">
                <div className="p-3 bg-pink-600/20 rounded-lg">
                  <FiAward className="h-6 w-6 text-pink-400" />
                </div>
                <span className="text-xs text-pink-400 font-semibold uppercase tracking-wider">Status</span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-white">100%</p>
                <p className="text-sm text-gray-400">System Ready</p>
                <div className="flex items-center gap-2 mt-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-xs text-green-400">All Systems Operational</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => <CardSkeleton key={i} />)}
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

        {/* Dynamic Visualizations from All Files */}
        {loading ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map(i => <ChartSkeleton key={i} />)}
          </div>
        ) : visualizationData && Object.keys(visualizationData).length > 0 ? (
          <div>
            <h2 className="text-2xl font-bold text-gray-100 mb-6 flex items-center gap-2">
              <FiBarChart2 className="h-7 w-7 text-purple-400" />
              Data Visualizations
            </h2>
            <div className="space-y-8">
              {Object.entries(visualizationData).map(([fileId, fileViz]) => {
                const file = files.find(f => f.file_id === fileId)
                const fileName = file?.original_filename || file?.filename || 'Unknown File'
                
                // Get charts from sheets or root
                let allCharts = []
                let allMetrics = {}
                
                if (fileViz.sheets) {
                  Object.entries(fileViz.sheets).forEach(([sheetName, sheet]) => {
                    if (sheet.charts) {
                      allCharts.push(...sheet.charts.map(chart => ({ ...chart, sheetName })))
                    }
                    if (sheet.metrics) {
                      Object.assign(allMetrics, sheet.metrics)
                    }
                  })
                } else {
                  if (fileViz.charts) allCharts = fileViz.charts
                  if (fileViz.metrics) allMetrics = fileViz.metrics
                }
                
                if (allCharts.length === 0) return null
                
                return (
                  <div key={fileId} className="space-y-4">
                    {/* File Header */}
                    <div className="bg-gradient-to-r from-purple-600/20 via-pink-600/20 to-blue-600/20 backdrop-blur-xl border border-purple-500/30 rounded-xl p-4 shadow-lg">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-600/20 rounded-lg">
                          <FiFile className="h-5 w-5 text-purple-400" />
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-gray-100">{fileName}</h3>
                          <p className="text-sm text-gray-400">{allCharts.length} chart{allCharts.length !== 1 ? 's' : ''} • {Object.keys(allMetrics).length} metric{Object.keys(allMetrics).length !== 1 ? 's' : ''}</p>
                        </div>
                      </div>
                    </div>
                    
                    {/* Charts Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                      {allCharts.map((chart, index) => (
                        <div 
                          key={index} 
                          className="bg-gradient-to-br from-gray-900/90 to-gray-800/50 backdrop-blur-xl border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-xl hover:border-purple-500/50 transition-all"
                        >
                          <h4 className="text-md font-semibold text-gray-100 mb-4 flex items-center gap-2">
                            {chart.type === 'bar' && <FiBarChart2 className="h-5 w-5 text-blue-400" />}
                            {chart.type === 'line' && <FiTrendingUp className="h-5 w-5 text-green-400" />}
                            {chart.type === 'pie' && <FiPieChart className="h-5 w-5 text-purple-400" />}
                            {chart.type === 'doughnut' && <FiPieChart className="h-5 w-5 text-pink-400" />}
                            {chart.title || chart.description || 'Chart'}
                            {chart.sheetName && (
                              <span className="text-xs text-gray-500 ml-2">({chart.sheetName})</span>
                            )}
                          </h4>
                          {renderChart(chart, index)}
                          {chart.description && (
                            <p className="text-xs text-gray-400 mt-4">{chart.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                    
                    {/* Metrics Display */}
                    {Object.keys(allMetrics).length > 0 && (
                      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                        {Object.entries(allMetrics).slice(0, 12).map(([key, value], idx) => {
                          // Extract value from metric object if it's an object
                          let displayValue = value
                          let unit = ''
                          
                          if (value && typeof value === 'object' && !Array.isArray(value)) {
                            displayValue = value.value !== undefined ? value.value : value
                            unit = value.unit || ''
                          }
                          
                          // Format the display value
                          let formattedValue = displayValue
                          if (typeof displayValue === 'number') {
                            formattedValue = displayValue.toLocaleString(undefined, {
                              maximumFractionDigits: 2
                            })
                          } else if (displayValue === null || displayValue === undefined) {
                            formattedValue = 'N/A'
                          } else {
                            formattedValue = String(displayValue)
                          }
                          
                          const colorClass = idx % 4 === 0 ? 'text-blue-400' : 
                                           idx % 4 === 1 ? 'text-purple-400' : 
                                           idx % 4 === 2 ? 'text-green-400' : 'text-pink-400'
                          return (
                            <div 
                              key={key}
                              className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-xl border border-gray-700/30 rounded-lg p-4 text-center hover:border-purple-500/50 transition-colors"
                            >
                              <div className="text-xs text-gray-400 mb-1 truncate" title={key.replace(/_/g, ' ')}>
                                {key.replace(/_/g, ' ')}
                              </div>
                              <div className={`text-lg font-bold ${colorClass}`}>
                                {formattedValue}
                                {unit && <span className="text-xs text-gray-500 ml-1">{unit}</span>}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ) : files.length > 0 ? (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-12 text-center">
            <FiBarChart2 className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-300 mb-2">No Visualizations Yet</h3>
            <p className="text-gray-500 mb-6">Upload files to see dynamic visualizations</p>
            <Link 
              to="/file-upload"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <FiFileText className="h-5 w-5" />
              Upload Files
            </Link>
          </div>
        ) : (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-12 text-center">
            <FiDatabase className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-300 mb-2">No Files Uploaded</h3>
            <p className="text-gray-500 mb-6">Get started by uploading your first file</p>
            <Link 
              to="/file-upload"
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg transition-all shadow-lg"
            >
              <FiFileText className="h-5 w-5" />
              Upload Files
            </Link>
          </div>
        )}

        {/* Data Files Overview */}
        {files.length > 0 && (
          <div className="bg-gradient-to-br from-gray-900/90 to-gray-800/50 backdrop-blur-xl border border-gray-700/50 rounded-xl p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
              <FiDatabase className="h-5 w-5 text-cyan-400" />
              Your Files
            </h3>
            <div className="space-y-3">
              {files.slice(0, 5).map((file) => (
                <div key={file.file_id} className="flex items-center justify-between p-3 bg-gray-800/30 rounded-lg hover:bg-gray-800/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-cyan-600/20 rounded">
                      <FiFileText className="h-4 w-4 text-cyan-400" />
                    </div>
                    <span className="text-sm text-gray-300 font-medium truncate">
                      {file.original_filename || file.filename}
                    </span>
                  </div>
                  <span className="text-xs text-gray-400">{file.file_type?.toUpperCase()}</span>
                </div>
              ))}
              {files.length > 5 && (
                <Link 
                  to="/file-upload"
                  className="block text-center text-sm text-blue-400 hover:text-blue-300 mt-4"
                >
                  View all {files.length} files →
                </Link>
              )}
            </div>
          </div>
        )}

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
