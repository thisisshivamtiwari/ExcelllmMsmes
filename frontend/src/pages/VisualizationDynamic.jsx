import { useState, useEffect } from "react"
import { FiBarChart2, FiTrendingUp, FiPieChart, FiRefreshCw, FiFilter, FiTable, FiFile, FiChevronDown, FiChevronUp, FiX, FiSearch, FiLink, FiLayers, FiCheckSquare, FiAlertCircle } from "react-icons/fi"
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend } from 'chart.js'
import { Bar, Line, Pie, Doughnut } from 'react-chartjs-2'
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

const VisualizationDynamic = () => {
  const { token } = useAuth()
  const [files, setFiles] = useState([])
  const [selectedFileId, setSelectedFileId] = useState(null)
  const [selectedSheet, setSelectedSheet] = useState(null)
  const [visualizationData, setVisualizationData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({})
  const [tableData, setTableData] = useState(null)
  const [tableLoading, setTableLoading] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(100)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedFileIds, setSelectedFileIds] = useState([])
  const [showMultiFileMode, setShowMultiFileMode] = useState(false)
  const [crossFileViz, setCrossFileViz] = useState(null)
  const [loadingCrossFile, setLoadingCrossFile] = useState(false)
  const [viewMode, setViewMode] = useState("single") // "single" or "multi"

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  // Load files on mount
  useEffect(() => {
    fetchFiles()
  }, [token])

  // Load visualizations when file is selected
  useEffect(() => {
    if (selectedFileId) {
      fetchVisualizations(selectedFileId)
      fetchFilterOptions(selectedFileId)
    }
  }, [selectedFileId, selectedSheet, token])
  
  // Load table data when filters change
  useEffect(() => {
    if (selectedFileId && showFilters) {
      // Debounce filter changes
      const timer = setTimeout(() => {
        fetchTableData(selectedFileId, selectedSheet, 1)
        setCurrentPage(1)
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [filters])

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
        // Auto-select first file if available
        if (data.files && data.files.length > 0 && !selectedFileId) {
          setSelectedFileId(data.files[0].file_id)
        }
      } else if (response.status === 401) {
        setError("Please login to view visualizations")
      }
    } catch (error) {
      console.error("Error fetching files:", error)
      setError(`Error: ${error.message}`)
    }
  }

  const fetchVisualizations = async (fileId) => {
    setLoading(true)
    setError(null)
    
    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const response = await fetch(`${API_BASE_URL}/visualizations/file/${fileId}`, { headers })
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.visualization) {
          setVisualizationData(data.visualization)
          
          // Auto-select first sheet for Excel files
          if (data.visualization.sheets && Object.keys(data.visualization.sheets).length > 0) {
            const firstSheet = Object.keys(data.visualization.sheets)[0]
            if (!selectedSheet) {
              setSelectedSheet(firstSheet)
            }
          }
        } else {
          setError("No visualization data available")
        }
      } else {
        const errorData = await response.json()
        setError(errorData.detail || "Failed to load visualizations")
      }
    } catch (error) {
      console.error("Error fetching visualizations:", error)
      setError(`Error: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const fetchCrossFileVisualizations = async () => {
    if (selectedFileIds.length < 2) {
      setError("Please select at least 2 files for cross-file analysis")
      return
    }
    
    setLoadingCrossFile(true)
    setError(null)
    
    try {
      const headers = {
        "Content-Type": "application/json"
      }
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const response = await fetch(`${API_BASE_URL}/visualizations/cross-file`, {
        method: "POST",
        headers,
        body: JSON.stringify(selectedFileIds)
      })
      
      if (response.ok) {
        const data = await response.json()
        console.log("Cross-file visualization response:", data)
        if (data.success && data.visualization) {
          console.log("Visualization data:", data.visualization)
          console.log("Charts:", data.visualization.charts)
          console.log("Relationship count:", data.visualization.relationship_count)
          setCrossFileViz(data.visualization)
        } else {
          setError("Failed to generate cross-file visualizations")
        }
      } else {
        const errorData = await response.json()
        setError(errorData.detail || "Failed to load cross-file visualizations")
      }
    } catch (error) {
      console.error("Error fetching cross-file visualizations:", error)
      setError(`Error: ${error.message}`)
    } finally {
      setLoadingCrossFile(false)
    }
  }

  const handleFileToggle = (fileId) => {
    setSelectedFileIds(prev => {
      if (prev.includes(fileId)) {
        return prev.filter(id => id !== fileId)
      } else {
        return [...prev, fileId]
      }
    })
  }

  const fetchFilterOptions = async (fileId) => {
    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const params = new URLSearchParams()
      if (selectedSheet) {
        params.append("sheet_name", selectedSheet)
      }
      
      const response = await fetch(`${API_BASE_URL}/visualizations/file/${fileId}/filter-options?${params}`, { headers })
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.columns) {
          setFilterOptions(data.columns)
        }
      }
    } catch (error) {
      console.error("Error fetching filter options:", error)
    }
  }

  const fetchTableData = async (fileId, sheetName = null, page = 1) => {
    setTableLoading(true)
    
    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      })
      
      if (sheetName) {
        params.append("sheet_name", sheetName)
      }
      
      if (Object.keys(filters).length > 0) {
        params.append("filters", JSON.stringify(filters))
      }
      
      const response = await fetch(`${API_BASE_URL}/visualizations/file/${fileId}/data?${params}`, { headers })
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setTableData(data)
        }
      }
    } catch (error) {
      console.error("Error fetching table data:", error)
    } finally {
      setTableLoading(false)
    }
  }

  const handleFilterChange = (column, value) => {
    setFilters(prev => {
      const newFilters = { ...prev }
      if (value === "" || value === null) {
        delete newFilters[column]
      } else {
        newFilters[column] = value
      }
      return newFilters
    })
  }

  const applyFilters = () => {
    if (selectedFileId) {
      fetchTableData(selectedFileId, selectedSheet, 1)
      setCurrentPage(1)
    }
  }

  const clearFilters = () => {
    setFilters({})
    if (selectedFileId) {
      fetchTableData(selectedFileId, selectedSheet, 1)
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

  const renderChart = (chart) => {
    const { type, title, data, description } = chart
    
    const chartData = {
      labels: data.labels || [],
      datasets: [{
        label: title,
        data: data.values || [],
        backgroundColor: type === 'pie' || type === 'doughnut' 
          ? colors.gradient.slice(0, data.labels?.length || 8)
          : colors.gradient[0],
        borderColor: colors.primary[0],
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
                  borderColor: '#10B981',
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
                  fill: true,
                  tension: 0.4
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

  const getCurrentVisualization = () => {
    if (!visualizationData) return null
    
    // Excel file with sheets
    if (visualizationData.sheets && selectedSheet) {
      return visualizationData.sheets[selectedSheet]
    }
    
    // CSV file or single sheet
    return visualizationData
  }

  const currentViz = getCurrentVisualization()
  const selectedFile = files.find(f => f.file_id === selectedFileId)

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-100 mb-2 flex items-center gap-2">
                <FiBarChart2 className="h-8 w-8" />
                Dynamic Data Visualizations
              </h1>
              <p className="text-gray-400">
                Auto-generated charts and tables for all your uploaded files
              </p>
            </div>
            <button
              onClick={() => {
                if (selectedFileId) {
                  fetchVisualizations(selectedFileId)
                } else {
                  fetchFiles()
                }
              }}
              className="px-4 py-2 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 transition-colors flex items-center gap-2"
            >
              <FiRefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Mode Toggle */}
        <div className="mb-4 flex gap-2">
          <button
            onClick={() => {
              setViewMode("single")
              setSelectedFileIds([])
              setCrossFileViz(null)
            }}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              viewMode === "single"
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800/50 text-gray-400 hover:bg-gray-800'
            }`}
          >
            <FiFile className="inline h-4 w-4 mr-2" />
            Single File
          </button>
          <button
            onClick={() => {
              setViewMode("multi")
              setSelectedFileId(null)
              setVisualizationData(null)
            }}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              viewMode === "multi"
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800/50 text-gray-400 hover:bg-gray-800'
            }`}
          >
            <FiLayers className="inline h-4 w-4 mr-2" />
            Cross-File Analysis
          </button>
        </div>

        {/* Single File Mode */}
        {viewMode === "single" && (
          <div className="mb-6 bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
            <div className="flex items-center gap-4 flex-wrap">
              <label className="text-sm font-medium text-gray-300">Select File:</label>
              <select
                value={selectedFileId || ""}
                onChange={(e) => {
                  setSelectedFileId(e.target.value)
                  setSelectedSheet(null)
                  setVisualizationData(null)
                  setTableData(null)
                }}
                className="flex-1 min-w-[200px] px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">-- Select a file --</option>
                {files.map((file) => (
                  <option key={file.file_id} value={file.file_id}>
                    {file.original_filename || file.filename} ({file.file_type?.toUpperCase()})
                  </option>
                ))}
              </select>
            
            {/* Sheet Selector (for Excel files) */}
            {visualizationData?.sheets && Object.keys(visualizationData.sheets).length > 1 && (
              <>
                <label className="text-sm font-medium text-gray-300">Sheet:</label>
                <select
                  value={selectedSheet || ""}
                  onChange={(e) => {
                    setSelectedSheet(e.target.value)
                    setTableData(null)
                  }}
                  className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Object.keys(visualizationData.sheets).map((sheet) => (
                    <option key={sheet} value={sheet}>
                      {sheet}
                    </option>
                  ))}
                </select>
              </>
            )}
          </div>
        </div>
        )}

        {/* Multi-File Mode */}
        {viewMode === "multi" && (
          <div className="mb-6 bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-gray-100 mb-2 flex items-center gap-2">
                <FiLink className="h-5 w-5" />
                Select Files for Cross-File Relationship Analysis
              </h3>
              <p className="text-sm text-gray-400 mb-4">
                Select 2 or more files to analyze relationships between them using Gemini API and semantic relationships
              </p>
            </div>
            
            {/* File Selection Checkboxes */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4 max-h-64 overflow-y-auto">
              {files.map((file) => (
                <label
                  key={file.file_id}
                  className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedFileIds.includes(file.file_id)
                      ? 'bg-blue-600/20 border-blue-500'
                      : 'bg-gray-800/50 border-gray-700 hover:bg-gray-800'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedFileIds.includes(file.file_id)}
                    onChange={() => handleFileToggle(file.file_id)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <FiFile className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-300 flex-1 truncate">
                    {file.original_filename || file.filename}
                  </span>
                  <span className="text-xs text-gray-500">
                    {file.file_type?.toUpperCase()}
                  </span>
                </label>
              ))}
            </div>
            
            {/* Generate Button */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-400">
                {selectedFileIds.length > 0 ? (
                  <span>{selectedFileIds.length} file{selectedFileIds.length !== 1 ? 's' : ''} selected</span>
                ) : (
                  <span>No files selected</span>
                )}
              </div>
              <button
                onClick={fetchCrossFileVisualizations}
                disabled={selectedFileIds.length < 2 || loadingCrossFile}
                className={`px-6 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                  selectedFileIds.length < 2 || loadingCrossFile
                    ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                {loadingCrossFile ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Generating...
                  </>
                ) : (
                  <>
                    <FiBarChart2 className="h-4 w-4" />
                    Generate Cross-File Visualizations
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-900/20 border border-red-800 text-red-300 flex items-center gap-2">
            <FiX className="h-5 w-5" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
              <p className="text-gray-400">Generating visualizations...</p>
            </div>
          </div>
        )}

        {/* Cross-File Visualizations */}
        {viewMode === "multi" && crossFileViz && !loadingCrossFile && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6">
                <div className="text-sm text-gray-400 mb-1">Files Analyzed</div>
                <div className="text-3xl font-bold text-gray-100">{crossFileViz.file_count}</div>
              </div>
              <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6">
                <div className="text-sm text-gray-400 mb-1">Relationships</div>
                <div className="text-3xl font-bold text-gray-100">{crossFileViz.relationship_count}</div>
              </div>
              <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6">
                <div className="text-sm text-gray-400 mb-1">Charts Generated</div>
                <div className="text-3xl font-bold text-gray-100">{crossFileViz.charts?.length || 0}</div>
              </div>
              <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6">
                <div className="text-sm text-gray-400 mb-1">File Connections</div>
                <div className="text-3xl font-bold text-gray-100">{crossFileViz.graph?.edge_count || 0}</div>
              </div>
            </div>

            {/* Cross-File Charts */}
            {crossFileViz.charts && crossFileViz.charts.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {crossFileViz.charts.map((chart, idx) => (
                  <div
                    key={idx}
                    className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg"
                  >
                    <h3 className="text-lg font-semibold text-gray-100 mb-2">{chart.title}</h3>
                    {chart.description && (
                      <p className="text-sm text-gray-400 mb-4">{chart.description}</p>
                    )}
                    {renderChart(chart)}
                  </div>
                ))}
              </div>
            )}
            
            {/* No Relationships Message */}
            {crossFileViz && crossFileViz.relationship_count === 0 && (
              <div className="mb-6 bg-yellow-900/20 border border-yellow-800/50 rounded-xl p-6">
                <div className="flex items-start gap-3">
                  <FiAlertCircle className="h-6 w-6 text-yellow-400 mt-1" />
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-yellow-300 mb-2">No Cross-File Relationships Found</h3>
                    <p className="text-yellow-200/80 mb-3">
                      No relationships were detected between the selected files. To discover relationships:
                    </p>
                    <ol className="list-decimal list-inside text-yellow-200/80 space-y-1 ml-2">
                      <li>Go to the <strong>File Upload</strong> page</li>
                      <li>Click <strong>"Analyze All Relationships"</strong> button</li>
                      <li>Wait for the analysis to complete (uses Gemini API)</li>
                      <li>Return here and generate cross-file visualizations again</li>
                    </ol>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Single File Visualizations */}
        {viewMode === "single" && !loading && currentViz && (
          <>
            {/* Metrics Cards */}
            {currentViz.metrics && Object.keys(currentViz.metrics).length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                {Object.entries(currentViz.metrics).map(([key, metric]) => (
                  <div
                    key={key}
                    className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg"
                  >
                    <div className="text-sm text-gray-400 mb-1">{key.replace(/_/g, ' ').toUpperCase()}</div>
                    <div className="text-3xl font-bold text-gray-100 mb-1">
                      {metric.value} {metric.unit && <span className="text-lg text-gray-400">{metric.unit}</span>}
                    </div>
                    {metric.formula && (
                      <div className="text-xs text-gray-500 mt-1">{metric.formula}</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Charts Grid */}
            {currentViz.charts && currentViz.charts.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {currentViz.charts.map((chart, idx) => (
                  <div
                    key={idx}
                    className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg"
                  >
                    <h3 className="text-lg font-semibold text-gray-100 mb-2">{chart.title}</h3>
                    {chart.description && (
                      <p className="text-sm text-gray-400 mb-4">{chart.description}</p>
                    )}
                    {renderChart(chart)}
                  </div>
                ))}
              </div>
            )}

            {/* Data Table Section */}
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl p-6 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-100 flex items-center gap-2">
                  <FiTable className="h-5 w-5" />
                  Data Table
                </h2>
                <button
                  onClick={() => {
                    setShowFilters(!showFilters)
                    if (!showFilters && selectedFileId) {
                      fetchTableData(selectedFileId, selectedSheet, currentPage)
                    }
                  }}
                  className="px-4 py-2 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 transition-colors flex items-center gap-2"
                >
                  <FiFilter className="h-4 w-4" />
                  Filters
                  {showFilters ? <FiChevronUp className="h-4 w-4" /> : <FiChevronDown className="h-4 w-4" />}
                </button>
              </div>

              {/* Filters Panel */}
              {showFilters && currentViz && (
                <div className="mb-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {currentViz.columns && currentViz.columns.slice(0, 9).map((col) => {
                      const colInfo = filterOptions[col] || {}
                      const colType = colInfo.type || 
                                     (currentViz.column_types?.categorical?.includes(col) ? 'categorical' :
                                     currentViz.column_types?.numeric?.includes(col) ? 'numeric' :
                                     currentViz.column_types?.date?.includes(col) ? 'date' : 'text')
                      
                      return (
                        <div key={col}>
                          <label className="block text-sm font-medium text-gray-300 mb-1">
                            {col}
                            {colInfo.unique_count && (
                              <span className="text-xs text-gray-500 ml-2">({colInfo.unique_count} unique)</span>
                            )}
                          </label>
                          {colType === 'categorical' && colInfo.options ? (
                            <select
                              value={filters[col] || ""}
                              onChange={(e) => handleFilterChange(col, e.target.value)}
                              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 text-sm"
                            >
                              <option value="">All</option>
                              {colInfo.options.map((opt) => (
                                <option key={opt} value={opt}>{opt}</option>
                              ))}
                            </select>
                          ) : colType === 'numeric' ? (
                            <div className="flex gap-2">
                              <input
                                type="number"
                                value={filters[`${col}_min`] || ""}
                                onChange={(e) => handleFilterChange(`${col}_min`, e.target.value)}
                                placeholder={colInfo.min !== undefined ? `Min: ${colInfo.min}` : "Min"}
                                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 text-sm"
                              />
                              <input
                                type="number"
                                value={filters[`${col}_max`] || ""}
                                onChange={(e) => handleFilterChange(`${col}_max`, e.target.value)}
                                placeholder={colInfo.max !== undefined ? `Max: ${colInfo.max}` : "Max"}
                                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 text-sm"
                              />
                            </div>
                          ) : colType === 'date' ? (
                            <div className="flex gap-2">
                              <input
                                type="date"
                                value={filters[`${col}_from`] || ""}
                                onChange={(e) => handleFilterChange(`${col}_from`, e.target.value)}
                                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 text-sm"
                              />
                              <input
                                type="date"
                                value={filters[`${col}_to`] || ""}
                                onChange={(e) => handleFilterChange(`${col}_to`, e.target.value)}
                                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 text-sm"
                              />
                            </div>
                          ) : (
                            <input
                              type="text"
                              value={filters[col] || ""}
                              onChange={(e) => handleFilterChange(col, e.target.value)}
                              placeholder={`Search ${col}...`}
                              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 text-sm"
                            />
                          )}
                        </div>
                      )
                    })}
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={applyFilters}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                    >
                      Apply Filters
                    </button>
                    <button
                      onClick={clearFilters}
                      className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors"
                    >
                      Clear All
                    </button>
                  </div>
                </div>
              )}

              {/* Table */}
              {tableData ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-gray-800/50 border-b border-gray-700">
                      <tr>
                        {tableData.columns && tableData.columns.map((col) => (
                          <th key={col} className="px-4 py-3 text-gray-300 font-semibold">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {tableData.data && tableData.data.map((row, idx) => (
                        <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/30">
                          {tableData.columns && tableData.columns.map((col) => (
                            <td key={col} className="px-4 py-3 text-gray-400">
                              {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  
                  {/* Pagination */}
                  {tableData.pagination && (
                    <div className="flex items-center justify-between mt-4">
                      <div className="text-sm text-gray-400">
                        Showing {((tableData.pagination.page - 1) * tableData.pagination.page_size) + 1} to{' '}
                        {Math.min(tableData.pagination.page * tableData.pagination.page_size, tableData.pagination.total_rows)} of{' '}
                        {tableData.pagination.total_rows} rows
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            const newPage = currentPage - 1
                            setCurrentPage(newPage)
                            fetchTableData(selectedFileId, selectedSheet, newPage)
                          }}
                          disabled={currentPage === 1}
                          className="px-4 py-2 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Previous
                        </button>
                        <span className="px-4 py-2 text-gray-300">
                          Page {currentPage} of {tableData.pagination.total_pages}
                        </span>
                        <button
                          onClick={() => {
                            const newPage = currentPage + 1
                            setCurrentPage(newPage)
                            fetchTableData(selectedFileId, selectedSheet, newPage)
                          }}
                          disabled={currentPage >= tableData.pagination.total_pages}
                          className="px-4 py-2 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12">
                  <button
                    onClick={() => fetchTableData(selectedFileId, selectedSheet, currentPage)}
                    className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                  >
                    {tableLoading ? "Loading..." : "Load Data Table"}
                  </button>
                </div>
              )}
            </div>
          </>
        )}

        {/* Empty State - Only show in single file mode */}
        {viewMode === "single" && !loading && !currentViz && !error && (
          <div className="text-center py-12 bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl">
            <FiFile className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-300 mb-2">No File Selected</h3>
            <p className="text-gray-400 mb-6">
              Select a file from the dropdown above to view dynamic visualizations
            </p>
          </div>
        )}

        {/* Empty State for Multi-File Mode */}
        {viewMode === "multi" && !crossFileViz && !loadingCrossFile && !error && (
          <div className="text-center py-12 bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-xl">
            <FiLayers className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-300 mb-2">No Cross-File Analysis Generated</h3>
            <p className="text-gray-400 mb-6">
              Select 2 or more files and click "Generate Cross-File Visualizations" to analyze relationships
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default VisualizationDynamic
