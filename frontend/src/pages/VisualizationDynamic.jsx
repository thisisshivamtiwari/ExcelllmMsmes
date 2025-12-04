import { useState, useEffect } from "react"
import { FiBarChart2, FiTrendingUp, FiPieChart, FiRefreshCw, FiTable, FiDatabase } from "react-icons/fi"
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend } from 'chart.js'
import { Bar, Line, Pie, Doughnut } from 'react-chartjs-2'
import DataViewer from "@/components/DataViewer"

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

const VisualizationDynamic = () => {
  const [visualizationData, setVisualizationData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeFile, setActiveFile] = useState(null)
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
      if (data.success && data.visualizations) {
        setVisualizationData(data.visualizations)
        // Auto-select first file
        const firstFile = Object.keys(data.visualizations)[0]
        if (firstFile) {
          setActiveFile(firstFile)
        }
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

  const pieOptions = {
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

  // Render a single chart
  const renderChart = (chart, index) => {
    const ChartComponent = {
      'bar': Bar,
      'line': Line,
      'pie': Pie,
      'doughnut': Doughnut
    }[chart.type] || Bar

    const chartData = {
      labels: chart.data.labels,
      datasets: [{
        label: chart.title,
        data: chart.data.values,
        backgroundColor: chart.type === 'line' ? 'rgba(59, 130, 246, 0.1)' : colors.gradient,
        borderColor: chart.type === 'line' ? '#3B82F6' : colors.primary,
        borderWidth: chart.type === 'line' ? 3 : 2,
        fill: chart.type === 'line',
        tension: chart.type === 'line' ? 0.4 : undefined,
        pointRadius: chart.type === 'line' ? 4 : undefined,
        pointHoverRadius: chart.type === 'line' ? 6 : undefined
      }]
    }

    const options = ['pie', 'doughnut'].includes(chart.type) ? pieOptions : chartOptions

    return (
      <div key={index} className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
        <h3 className="text-lg font-semibold text-gray-100 mb-2">{chart.title}</h3>
        {chart.description && (
          <p className="text-sm text-gray-400 mb-4">{chart.description}</p>
        )}
        <div className="h-80">
          <ChartComponent data={chartData} options={options} />
        </div>
      </div>
    )
  }

  // Render metrics
  const renderMetrics = (metrics) => {
    if (!metrics || Object.keys(metrics).length === 0) return null

    return (
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-gray-100 mb-4">Key Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(metrics).map(([key, metric]) => (
            <div key={key} className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-4 shadow-lg">
              <p className="text-sm text-gray-400 mb-1">{key.replace(/_/g, ' ').toUpperCase()}</p>
              <p className="text-2xl font-bold text-gray-100">{metric.value.toLocaleString()}</p>
              {metric.unit && (
                <p className="text-xs text-gray-500 mt-1">{metric.unit}</p>
              )}
              {metric.formula && (
                <p className="text-xs text-gray-600 mt-2 font-mono">{metric.formula}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Get available files for tabs
  const availableFiles = visualizationData ? Object.keys(visualizationData) : []
  const availableDataFiles = Object.keys(existingFiles).filter(
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

  const currentFileData = activeFile && visualizationData ? visualizationData[activeFile] : null

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-100 mb-2 flex items-center gap-2">
                <FiBarChart2 className="h-8 w-8" />
                Dynamic Data Visualizations
              </h1>
              <p className="text-gray-400">
                Automatically generated charts for all your data files
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

        {/* File Tabs */}
        {availableFiles.length > 0 && (
          <div className="mb-6 flex flex-wrap gap-2">
            {availableFiles.map((fileName) => (
              <button
                key={fileName}
                onClick={() => setActiveFile(fileName)}
                className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                  activeFile === fileName
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-gray-800/50 text-gray-400 hover:bg-gray-800 hover:text-gray-300'
                }`}
              >
                <FiDatabase className="h-4 w-4" />
                {fileName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </button>
            ))}
            <button
              onClick={() => setActiveFile('data_tables')}
              className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                activeFile === 'data_tables'
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-gray-800/50 text-gray-400 hover:bg-gray-800 hover:text-gray-300'
              }`}
            >
              <FiTable className="h-4 w-4" />
              Data Tables
            </button>
          </div>
        )}

        {/* File Info */}
        {currentFileData && activeFile !== 'data_tables' && (
          <div className="mb-6 bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-4 shadow-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6 text-sm text-gray-400">
                <div>
                  <span className="text-gray-500">Rows:</span>{' '}
                  <span className="font-medium text-gray-300">{currentFileData.row_count?.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-gray-500">Columns:</span>{' '}
                  <span className="font-medium text-gray-300">{currentFileData.column_count}</span>
                </div>
                <div>
                  <span className="text-gray-500">Charts:</span>{' '}
                  <span className="font-medium text-gray-300">{currentFileData.charts?.length || 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Content */}
        {activeFile === 'data_tables' ? (
          // Data Tables View
          <div>
            {availableDataFiles.length > 0 ? (
              <div>
                <div className="mb-4">
                  <h2 className="text-xl font-semibold text-gray-100 mb-1">
                    Interactive Data Explorer
                  </h2>
                  <p className="text-sm text-gray-400">
                    Browse, search, and analyze all your data files in detail
                  </p>
                </div>
                <DataViewer fileNames={availableDataFiles} API_BASE_URL={API_BASE_URL} />
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
        ) : currentFileData ? (
          // Charts View
          <div className="space-y-6">
            {/* Metrics */}
            {currentFileData.metrics && renderMetrics(currentFileData.metrics)}

            {/* Charts */}
            {currentFileData.charts && currentFileData.charts.length > 0 ? (
              <div>
                <h3 className="text-xl font-semibold text-gray-100 mb-4">Visualizations</h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {currentFileData.charts.map((chart, index) => renderChart(chart, index))}
                </div>
              </div>
            ) : (
              <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-12 shadow-lg text-center">
                <FiPieChart className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-300 mb-2">No Charts Available</h3>
                <p className="text-gray-400">
                  No visualizations could be generated for this file
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-12 shadow-lg text-center">
            <FiBarChart2 className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-300 mb-2">No Data Available</h3>
            <p className="text-gray-400 mb-6">
              Generate some data first to visualize it here
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
    </div>
  )
}

export default VisualizationDynamic

