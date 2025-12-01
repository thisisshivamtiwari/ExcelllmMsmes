import { useState, useEffect } from "react"
import { FiBarChart2, FiTrendingUp, FiPieChart, FiRefreshCw } from "react-icons/fi"
import DataViewer from "@/components/DataViewer"

const Visualization = () => {
  const [existingFiles, setExistingFiles] = useState({})
  const [selectedFile, setSelectedFile] = useState(null)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  useEffect(() => {
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

  // Get list of available files
  const availableFiles = Object.keys(existingFiles).filter(
    (fileName) => existingFiles[fileName]?.exists
  )

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-100 mb-2 flex items-center gap-2">
            <FiBarChart2 className="h-8 w-8" />
            Data Visualization
          </h1>
          <p className="text-gray-400">
            Visualize and analyze your generated manufacturing data with interactive charts and detailed views
          </p>
        </div>

        {/* Stats Cards */}
        {Object.keys(existingFiles).length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
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
                    <FiBarChart2 className="h-5 w-5 text-gray-500" />
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

        {/* Data Viewer Section */}
        {availableFiles.length > 0 ? (
          <div>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-100 mb-1">
                  Interactive Data Explorer
                </h2>
                <p className="text-sm text-gray-400">
                  Browse, search, and analyze your generated data in detail
                </p>
              </div>
              <button
                onClick={fetchExistingFiles}
                className="px-4 py-2 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 transition-colors flex items-center gap-2"
                tabIndex={0}
              >
                <FiRefreshCw className="h-4 w-4" />
                Refresh
              </button>
            </div>
            <DataViewer fileNames={availableFiles} API_BASE_URL={API_BASE_URL} />
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

        {/* Future: Chart Visualizations Section */}
        {availableFiles.length > 0 && (
          <div className="mt-8">
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
              <h2 className="text-xl font-semibold text-gray-100 mb-4 flex items-center gap-2">
                <FiTrendingUp className="h-5 w-5" />
                Chart Visualizations
              </h2>
              <div className="bg-gray-800/30 border border-gray-700/50 rounded-lg p-8 text-center">
                <FiPieChart className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">
                  Chart visualizations will be available here soon
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Features: Line charts, bar charts, pie charts, and more
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Visualization

