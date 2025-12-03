import { useState, useEffect } from "react"
import { FiBarChart2, FiTrendingUp, FiPieChart, FiRefreshCw, FiActivity, FiPackage, FiTool, FiBox, FiTable } from "react-icons/fi"
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, RadarController, RadialLinearScale, Title, Tooltip, Legend } from 'chart.js'
import { Bar, Line, Pie, Doughnut, Radar } from 'react-chartjs-2'
import DataViewer from "@/components/DataViewer"

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  RadarController,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend
)

const Visualization = () => {
  const [visualizationData, setVisualizationData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('production')
  const [existingFiles, setExistingFiles] = useState({})

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  useEffect(() => {
    fetchVisualizationData()
    fetchExistingFiles()
  }, [])

  const fetchExistingFiles = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/files`)
      const data = await response.json()
      setExistingFiles(data.files || {})
    } catch (error) {
      console.error("Error fetching files:", error)
    }
  }

  const fetchVisualizationData = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE_URL}/visualizations/data/all`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      if (data.success) {
        setVisualizationData(data.visualizations)
      } else {
        throw new Error("Failed to fetch visualization data")
      }
    } catch (error) {
      console.error("Error fetching visualization data:", error)
      setError(error.message)
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
        grid: { color: 'rgba(75, 85, 99, 0.2)' }
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

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: '#E5E7EB',
          font: { size: 12 }
        }
      }
    },
    scales: {
      r: {
        ticks: { color: '#9CA3AF', backdropColor: 'transparent' },
        grid: { color: 'rgba(75, 85, 99, 0.3)' },
        pointLabels: { color: '#E5E7EB', font: { size: 11 } }
      }
    }
  }

  // Color palettes
  const colors = {
    primary: ['#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#06B6D4', '#6366F1', '#EF4444'],
    gradient: [
      'rgba(59, 130, 246, 0.8)',
      'rgba(139, 92, 246, 0.8)',
      'rgba(236, 72, 153, 0.8)',
      'rgba(245, 158, 11, 0.8)',
      'rgba(16, 185, 129, 0.8)',
      'rgba(6, 182, 212, 0.8)',
      'rgba(99, 102, 241, 0.8)',
      'rgba(239, 68, 68, 0.8)'
    ]
  }

  // Render chart section
  const renderChartSection = (title, icon, children) => (
    <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
      <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      {children}
    </div>
  )

  // Production Visualizations
  const renderProductionCharts = () => {
    if (!visualizationData?.production) return null

    const { by_product, trend, by_shift, by_line, downtime_by_line, target_vs_actual, efficiency_by_product } = visualizationData.production

    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Production by Product - Bar Chart */}
        {renderChartSection(
          "Production by Product",
          <FiBarChart2 className="h-5 w-5 text-blue-400" />,
          <div className="h-80">
            <Bar
              data={{
                labels: Object.keys(by_product),
                datasets: [{
                  label: 'Total Production (units)',
                  data: Object.values(by_product),
                  backgroundColor: colors.gradient,
                  borderColor: colors.primary,
                  borderWidth: 2
                }]
              }}
              options={chartOptions}
            />
          </div>
        )}

        {/* Production Trend - Line Chart */}
        {renderChartSection(
          "Production Trend (Last 30 Days)",
          <FiTrendingUp className="h-5 w-5 text-green-400" />,
          <div className="h-80">
            <Line
              data={{
                labels: trend.labels,
                datasets: [{
                  label: 'Daily Production',
                  data: trend.values,
                  borderColor: '#10B981',
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
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
        )}

        {/* Production by Shift - Pie Chart */}
        {renderChartSection(
          "Production Distribution by Shift",
          <FiPieChart className="h-5 w-5 text-purple-400" />,
          <div className="h-80">
            <Pie
              data={{
                labels: Object.keys(by_shift),
                datasets: [{
                  data: Object.values(by_shift),
                  backgroundColor: colors.gradient,
                  borderColor: '#1F2937',
                  borderWidth: 2
                }]
              }}
              options={pieOptions}
            />
          </div>
        )}

        {/* Production by Line - Doughnut Chart */}
        {renderChartSection(
          "Production by Line/Machine",
          <FiActivity className="h-5 w-5 text-cyan-400" />,
          <div className="h-80">
            <Doughnut
              data={{
                labels: Object.keys(by_line),
                datasets: [{
                  data: Object.values(by_line),
                  backgroundColor: colors.gradient,
                  borderColor: '#1F2937',
                  borderWidth: 2
                }]
              }}
              options={pieOptions}
            />
          </div>
        )}

        {/* Downtime Analysis - Bar Chart */}
        {renderChartSection(
          "Downtime by Line (Minutes)",
          <FiTool className="h-5 w-5 text-red-400" />,
          <div className="h-80">
            <Bar
              data={{
                labels: Object.keys(downtime_by_line),
                datasets: [{
                  label: 'Downtime (minutes)',
                  data: Object.values(downtime_by_line),
                  backgroundColor: 'rgba(239, 68, 68, 0.8)',
                  borderColor: '#EF4444',
                  borderWidth: 2
                }]
              }}
              options={chartOptions}
            />
          </div>
        )}

        {/* Target vs Actual - Bar Chart */}
        {renderChartSection(
          "Target vs Actual Production",
          <FiBarChart2 className="h-5 w-5 text-yellow-400" />,
          <div className="h-80">
            <Bar
              data={{
                labels: Object.keys(target_vs_actual),
                datasets: [{
                  label: 'Quantity',
                  data: Object.values(target_vs_actual),
                  backgroundColor: ['rgba(245, 158, 11, 0.8)', 'rgba(16, 185, 129, 0.8)'],
                  borderColor: ['#F59E0B', '#10B981'],
                  borderWidth: 2
                }]
              }}
              options={chartOptions}
            />
          </div>
        )}

        {/* Efficiency by Product - Radar Chart */}
        {renderChartSection(
          "Efficiency by Product (%)",
          <FiActivity className="h-5 w-5 text-indigo-400" />,
          <div className="h-80">
            <Radar
              data={{
                labels: Object.keys(efficiency_by_product),
                datasets: [{
                  label: 'Efficiency %',
                  data: Object.values(efficiency_by_product),
                  backgroundColor: 'rgba(99, 102, 241, 0.2)',
                  borderColor: '#6366F1',
                  borderWidth: 2,
                  pointBackgroundColor: '#6366F1',
                  pointBorderColor: '#fff',
                  pointHoverBackgroundColor: '#fff',
                  pointHoverBorderColor: '#6366F1'
                }]
              }}
              options={radarOptions}
            />
          </div>
        )}
      </div>
    )
  }

  // Quality Control Visualizations
  const renderQualityCharts = () => {
    if (!visualizationData?.quality) return null

    const { defects_by_type, pass_rate_by_product, quality_trend, defects_by_product, rework_by_product } = visualizationData.quality

    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Defects by Type - Pie Chart */}
        {renderChartSection(
          "Defects by Type",
          <FiPieChart className="h-5 w-5 text-red-400" />,
          <div className="h-80">
            <Pie
              data={{
                labels: Object.keys(defects_by_type),
                datasets: [{
                  data: Object.values(defects_by_type),
                  backgroundColor: colors.gradient,
                  borderColor: '#1F2937',
                  borderWidth: 2
                }]
              }}
              options={pieOptions}
            />
          </div>
        )}

        {/* Pass Rate by Product - Bar Chart */}
        {renderChartSection(
          "Pass Rate by Product (%)",
          <FiBarChart2 className="h-5 w-5 text-green-400" />,
          <div className="h-80">
            <Bar
              data={{
                labels: Object.keys(pass_rate_by_product),
                datasets: [{
                  label: 'Pass Rate %',
                  data: Object.values(pass_rate_by_product),
                  backgroundColor: 'rgba(16, 185, 129, 0.8)',
                  borderColor: '#10B981',
                  borderWidth: 2
                }]
              }}
              options={{
                ...chartOptions,
                scales: {
                  ...chartOptions.scales,
                  y: {
                    ...chartOptions.scales.y,
                    min: 0,
                    max: 100
                  }
                }
              }}
            />
          </div>
        )}

        {/* Quality Trend - Line Chart */}
        {renderChartSection(
          "Quality Trend (Last 30 Days)",
          <FiTrendingUp className="h-5 w-5 text-blue-400" />,
          <div className="h-80">
            <Line
              data={{
                labels: quality_trend.labels,
                datasets: [{
                  label: 'Pass Rate %',
                  data: quality_trend.values,
                  borderColor: '#3B82F6',
                  backgroundColor: 'rgba(59, 130, 246, 0.1)',
                  borderWidth: 3,
                  fill: true,
                  tension: 0.4,
                  pointRadius: 4,
                  pointHoverRadius: 6
                }]
              }}
              options={{
                ...chartOptions,
                scales: {
                  ...chartOptions.scales,
                  y: {
                    ...chartOptions.scales.y,
                    min: 0,
                    max: 100
                  }
                }
              }}
            />
          </div>
        )}

        {/* Defects by Product - Bar Chart */}
        {renderChartSection(
          "Total Defects by Product",
          <FiBarChart2 className="h-5 w-5 text-orange-400" />,
          <div className="h-80">
            <Bar
              data={{
                labels: Object.keys(defects_by_product),
                datasets: [{
                  label: 'Failed Quantity',
                  data: Object.values(defects_by_product),
                  backgroundColor: 'rgba(245, 158, 11, 0.8)',
                  borderColor: '#F59E0B',
                  borderWidth: 2
                }]
              }}
              options={chartOptions}
            />
          </div>
        )}

        {/* Rework Analysis - Doughnut Chart */}
        {renderChartSection(
          "Rework Count by Product",
          <FiActivity className="h-5 w-5 text-purple-400" />,
          <div className="h-80">
            <Doughnut
              data={{
                labels: Object.keys(rework_by_product),
                datasets: [{
                  data: Object.values(rework_by_product),
                  backgroundColor: colors.gradient,
                  borderColor: '#1F2937',
                  borderWidth: 2
                }]
              }}
              options={pieOptions}
            />
          </div>
        )}

        {/* Pass Rate Radar */}
        {renderChartSection(
          "Quality Performance Radar",
          <FiActivity className="h-5 w-5 text-cyan-400" />,
          <div className="h-80">
            <Radar
              data={{
                labels: Object.keys(pass_rate_by_product),
                datasets: [{
                  label: 'Pass Rate %',
                  data: Object.values(pass_rate_by_product),
                  backgroundColor: 'rgba(6, 182, 212, 0.2)',
                  borderColor: '#06B6D4',
                  borderWidth: 2,
                  pointBackgroundColor: '#06B6D4',
                  pointBorderColor: '#fff',
                  pointHoverBackgroundColor: '#fff',
                  pointHoverBorderColor: '#06B6D4'
                }]
              }}
              options={radarOptions}
            />
          </div>
        )}
      </div>
    )
  }

  // Maintenance Visualizations
  const renderMaintenanceCharts = () => {
    if (!visualizationData?.maintenance) return null

    const { by_type, downtime_by_machine, cost_by_machine, maintenance_trend, cost_trend } = visualizationData.maintenance

    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Maintenance by Type - Pie Chart */}
        {renderChartSection(
          "Maintenance Activities by Type",
          <FiPieChart className="h-5 w-5 text-blue-400" />,
          <div className="h-80">
            <Pie
              data={{
                labels: Object.keys(by_type),
                datasets: [{
                  data: Object.values(by_type),
                  backgroundColor: colors.gradient,
                  borderColor: '#1F2937',
                  borderWidth: 2
                }]
              }}
              options={pieOptions}
            />
          </div>
        )}

        {/* Downtime by Machine - Bar Chart */}
        {renderChartSection(
          "Downtime by Machine (Hours)",
          <FiBarChart2 className="h-5 w-5 text-red-400" />,
          <div className="h-80">
            <Bar
              data={{
                labels: Object.keys(downtime_by_machine),
                datasets: [{
                  label: 'Downtime (hours)',
                  data: Object.values(downtime_by_machine),
                  backgroundColor: 'rgba(239, 68, 68, 0.8)',
                  borderColor: '#EF4444',
                  borderWidth: 2
                }]
              }}
              options={chartOptions}
            />
          </div>
        )}

        {/* Cost by Machine - Bar Chart */}
        {renderChartSection(
          "Maintenance Cost by Machine (₹)",
          <FiBarChart2 className="h-5 w-5 text-yellow-400" />,
          <div className="h-80">
            <Bar
              data={{
                labels: Object.keys(cost_by_machine),
                datasets: [{
                  label: 'Cost (₹)',
                  data: Object.values(cost_by_machine),
                  backgroundColor: 'rgba(245, 158, 11, 0.8)',
                  borderColor: '#F59E0B',
                  borderWidth: 2
                }]
              }}
              options={chartOptions}
            />
          </div>
        )}

        {/* Maintenance Trend - Line Chart */}
        {renderChartSection(
          "Maintenance Activity Trend",
          <FiTrendingUp className="h-5 w-5 text-green-400" />,
          <div className="h-80">
            <Line
              data={{
                labels: maintenance_trend.labels,
                datasets: [{
                  label: 'Number of Activities',
                  data: maintenance_trend.values,
                  borderColor: '#10B981',
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
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
        )}

        {/* Cost Trend - Line Chart */}
        {renderChartSection(
          "Maintenance Cost Trend (₹)",
          <FiTrendingUp className="h-5 w-5 text-purple-400" />,
          <div className="h-80">
            <Line
              data={{
                labels: cost_trend.labels,
                datasets: [{
                  label: 'Cost (₹)',
                  data: cost_trend.values,
                  borderColor: '#8B5CF6',
                  backgroundColor: 'rgba(139, 92, 246, 0.1)',
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
        )}

        {/* Machine Performance Radar */}
        {renderChartSection(
          "Machine Reliability (Inverse Downtime)",
          <FiActivity className="h-5 w-5 text-cyan-400" />,
          <div className="h-80">
            <Radar
              data={{
                labels: Object.keys(downtime_by_machine),
                datasets: [{
                  label: 'Reliability Score',
                  data: Object.values(downtime_by_machine).map(v => Math.max(0, 100 - v * 2)),
                  backgroundColor: 'rgba(6, 182, 212, 0.2)',
                  borderColor: '#06B6D4',
                  borderWidth: 2,
                  pointBackgroundColor: '#06B6D4',
                  pointBorderColor: '#fff',
                  pointHoverBackgroundColor: '#fff',
                  pointHoverBorderColor: '#06B6D4'
                }]
              }}
              options={radarOptions}
            />
          </div>
        )}
      </div>
    )
  }

  // Inventory Visualizations
  const renderInventoryCharts = () => {
    if (!visualizationData?.inventory) return null

    const { stock_by_material, consumption_by_material, wastage_by_material, stock_trend, cost_by_supplier } = visualizationData.inventory

    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Stock by Material - Bar Chart */}
        {renderChartSection(
          "Current Stock by Material (Kg)",
          <FiBarChart2 className="h-5 w-5 text-blue-400" />,
          <div className="h-80">
            <Bar
              data={{
                labels: Object.keys(stock_by_material),
                datasets: [{
                  label: 'Stock (Kg)',
                  data: Object.values(stock_by_material),
                  backgroundColor: colors.gradient,
                  borderColor: colors.primary,
                  borderWidth: 2
                }]
              }}
              options={chartOptions}
            />
          </div>
        )}

        {/* Consumption by Material - Doughnut Chart */}
        {renderChartSection(
          "Material Consumption Distribution",
          <FiPieChart className="h-5 w-5 text-green-400" />,
          <div className="h-80">
            <Doughnut
              data={{
                labels: Object.keys(consumption_by_material),
                datasets: [{
                  data: Object.values(consumption_by_material),
                  backgroundColor: colors.gradient,
                  borderColor: '#1F2937',
                  borderWidth: 2
                }]
              }}
              options={pieOptions}
            />
          </div>
        )}

        {/* Wastage by Material - Bar Chart */}
        {renderChartSection(
          "Wastage by Material (Kg)",
          <FiBarChart2 className="h-5 w-5 text-red-400" />,
          <div className="h-80">
            <Bar
              data={{
                labels: Object.keys(wastage_by_material),
                datasets: [{
                  label: 'Wastage (Kg)',
                  data: Object.values(wastage_by_material),
                  backgroundColor: 'rgba(239, 68, 68, 0.8)',
                  borderColor: '#EF4444',
                  borderWidth: 2
                }]
              }}
              options={chartOptions}
            />
          </div>
        )}

        {/* Stock Trend - Line Chart */}
        {renderChartSection(
          "Stock Level Trend (Last 30 Days)",
          <FiTrendingUp className="h-5 w-5 text-purple-400" />,
          <div className="h-80">
            <Line
              data={{
                labels: stock_trend.labels,
                datasets: [{
                  label: 'Total Stock (Kg)',
                  data: stock_trend.values,
                  borderColor: '#8B5CF6',
                  backgroundColor: 'rgba(139, 92, 246, 0.1)',
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
        )}

        {/* Cost by Supplier - Bar Chart */}
        {renderChartSection(
          "Average Unit Cost by Supplier (₹)",
          <FiBarChart2 className="h-5 w-5 text-yellow-400" />,
          <div className="h-80">
            <Bar
              data={{
                labels: Object.keys(cost_by_supplier),
                datasets: [{
                  label: 'Unit Cost (₹)',
                  data: Object.values(cost_by_supplier),
                  backgroundColor: 'rgba(245, 158, 11, 0.8)',
                  borderColor: '#F59E0B',
                  borderWidth: 2
                }]
              }}
              options={chartOptions}
            />
          </div>
        )}

        {/* Material Stock Radar */}
        {renderChartSection(
          "Material Stock Levels Radar",
          <FiActivity className="h-5 w-5 text-cyan-400" />,
          <div className="h-80">
            <Radar
              data={{
                labels: Object.keys(stock_by_material),
                datasets: [{
                  label: 'Stock (Kg)',
                  data: Object.values(stock_by_material),
                  backgroundColor: 'rgba(6, 182, 212, 0.2)',
                  borderColor: '#06B6D4',
                  borderWidth: 2,
                  pointBackgroundColor: '#06B6D4',
                  pointBorderColor: '#fff',
                  pointHoverBackgroundColor: '#fff',
                  pointHoverBorderColor: '#06B6D4'
                }]
              }}
              options={radarOptions}
            />
          </div>
        )}
      </div>
    )
  }

  const tabs = [
    { id: 'production', label: 'Production', icon: <FiActivity className="h-4 w-4" /> },
    { id: 'quality', label: 'Quality Control', icon: <FiPieChart className="h-4 w-4" /> },
    { id: 'maintenance', label: 'Maintenance', icon: <FiTool className="h-4 w-4" /> },
    { id: 'inventory', label: 'Inventory', icon: <FiBox className="h-4 w-4" /> },
    { id: 'data', label: 'Data Tables', icon: <FiTable className="h-4 w-4" /> }
  ]

  // Get list of available files for data viewer
  const availableFiles = Object.keys(existingFiles).filter(
    (fileName) => existingFiles[fileName]?.exists
  )

  if (loading) {
    return (
      <div className="p-4 md:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
              <p className="text-gray-400">Loading visualizations...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 md:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-6 text-center">
            <p className="text-red-400 mb-4">Error loading visualizations: {error}</p>
            <button
              onClick={fetchVisualizationData}
              className="px-4 py-2 bg-red-800/50 hover:bg-red-800 border border-red-700 rounded-lg text-gray-300 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-100 mb-2 flex items-center gap-2">
                <FiBarChart2 className="h-8 w-8" />
                Data Visualizations
              </h1>
              <p className="text-gray-400">
                Comprehensive charts and analytics from all manufacturing data files
              </p>
            </div>
            <button
              onClick={fetchVisualizationData}
              className="px-4 py-2 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 transition-colors flex items-center gap-2"
              tabIndex={0}
            >
              <FiRefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-gray-800/50 text-gray-400 hover:bg-gray-800 hover:text-gray-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Stats Cards */}
        {activeTab === 'data' && Object.keys(existingFiles).length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {Object.entries(existingFiles).map(([fileName, fileInfo]) => {
              if (!fileInfo.exists) return null
              return (
                <div
                  key={fileName}
                  className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-400">
                      {fileName.replace(".csv", "").replace("_", " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                    </h3>
                    <FiTable className="h-5 w-5 text-gray-500" />
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-gray-100">
                      {fileInfo.rows?.toLocaleString() || 0}
                    </span>
                    <span className="text-sm text-gray-400">rows</span>
                  </div>
                  <div className="mt-2 text-xs text-gray-500">
                    {(fileInfo.size_bytes / 1024).toFixed(2)} KB
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Chart Content */}
        <div className="space-y-6">
          {activeTab === 'production' && renderProductionCharts()}
          {activeTab === 'quality' && renderQualityCharts()}
          {activeTab === 'maintenance' && renderMaintenanceCharts()}
          {activeTab === 'inventory' && renderInventoryCharts()}
          
          {/* Data Tables Tab */}
          {activeTab === 'data' && (
            <div>
              {availableFiles.length > 0 ? (
                <div>
                  <div className="mb-4">
                    <h2 className="text-xl font-semibold text-gray-100 mb-1">
                      Interactive Data Explorer
                    </h2>
                    <p className="text-sm text-gray-400">
                      Browse, search, and analyze all your data files in detail
                    </p>
                  </div>
                  <DataViewer fileNames={availableFiles} API_BASE_URL={API_BASE_URL} />
                </div>
              ) : (
                <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-12 shadow-lg text-center">
                  <FiTable className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-gray-300 mb-2">No Data Available</h3>
                  <p className="text-gray-400 mb-6">
                    Generate or upload data files to view them here
                  </p>
                  <a
                    href="/data-generator"
                    className="inline-block px-6 py-3 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-300 transition-colors"
                  >
                    Go to Data Generator
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Visualization
