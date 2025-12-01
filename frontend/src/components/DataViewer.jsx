import { useState, useEffect } from "react"
import { FiSearch, FiChevronLeft, FiChevronRight, FiDownload, FiRefreshCw } from "react-icons/fi"

const DataViewer = ({ fileNames, API_BASE_URL }) => {
  const [activeFile, setActiveFile] = useState(null)
  const [data, setData] = useState([])
  const [columns, setColumns] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // Pagination
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(50)
  const [pagination, setPagination] = useState(null)
  
  // Search
  const [searchTerm, setSearchTerm] = useState("")
  const [searchInput, setSearchInput] = useState("")

  // Auto-select first file when fileNames change
  useEffect(() => {
    if (fileNames && fileNames.length > 0 && !activeFile) {
      setActiveFile(fileNames[0])
    }
  }, [fileNames])

  useEffect(() => {
    if (activeFile) {
      fetchData()
      fetchStats()
    }
  }, [activeFile, page, limit, searchTerm])

  const fetchData = async () => {
    if (!activeFile) return
    
    setLoading(true)
    setError(null)
    
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
      })
      
      if (searchTerm) {
        params.append("search", searchTerm)
      }
      
      const response = await fetch(`${API_BASE_URL}/data/${activeFile}?${params}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch data: ${response.statusText}`)
      }
      
      const result = await response.json()
      setData(result.data || [])
      setColumns(result.columns || [])
      setPagination(result.pagination || null)
    } catch (err) {
      setError(err.message)
      setData([])
      setColumns([])
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    if (!activeFile) return
    
    try {
      const response = await fetch(`${API_BASE_URL}/data/${activeFile}/stats`)
      if (response.ok) {
        const statsData = await response.json()
        setStats(statsData)
      }
    } catch (err) {
      console.error("Error fetching stats:", err)
    }
  }

  const handleSearch = () => {
    setSearchTerm(searchInput)
    setPage(1) // Reset to first page on new search
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      handleSearch()
    }
  }

  const handleFileSelect = (fileName) => {
    setActiveFile(fileName)
    setPage(1)
    setSearchTerm("")
    setSearchInput("")
  }

  const formatValue = (value, columnName) => {
    if (value === null || value === undefined || value === "") {
      return <span className="text-gray-500">—</span>
    }
    
    // Format dates
    if (columnName.toLowerCase().includes("date")) {
      try {
        const date = new Date(value)
        if (!isNaN(date.getTime())) {
          return date.toLocaleDateString()
        }
      } catch (e) {
        // Not a valid date
      }
    }
    
    // Format numbers
    if (typeof value === "string" && /^\d+\.?\d*$/.test(value.trim())) {
      const num = parseFloat(value)
      if (!isNaN(num)) {
        return num.toLocaleString()
      }
    }
    
    return value
  }

  if (!fileNames || fileNames.length === 0) {
    return (
      <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
        <p className="text-gray-400 text-center">No data files available</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg shadow-lg overflow-hidden">
      {/* File Tabs */}
      <div className="border-b border-gray-800/50 bg-gray-800/30">
        <div className="flex overflow-x-auto">
          {fileNames.map((fileName) => (
            <button
              key={fileName}
              onClick={() => handleFileSelect(fileName)}
              className={`px-6 py-3 text-sm font-medium transition-colors whitespace-nowrap border-b-2 ${
                activeFile === fileName
                  ? "border-blue-500 text-blue-400 bg-gray-900/50"
                  : "border-transparent text-gray-400 hover:text-gray-300 hover:bg-gray-800/30"
              }`}
              tabIndex={0}
            >
              {fileName.replace(".csv", "").replace("_", " ").replace(/\b\w/g, (l) => l.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      {activeFile && (
        <div className="p-6">
          {/* Stats and Search Bar */}
          <div className="mb-6 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
            {stats && (
              <div className="text-sm text-gray-400">
                <span className="font-medium text-gray-300">{stats.total_rows.toLocaleString()}</span> rows •{" "}
                <span className="font-medium text-gray-300">{stats.columns.length}</span> columns •{" "}
                <span className="font-medium text-gray-300">
                  {(stats.file_size_bytes / 1024).toFixed(2)} KB
                </span>
              </div>
            )}
            
            <div className="flex gap-2 flex-1 md:flex-initial md:max-w-md">
              <div className="relative flex-1">
                <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Search in data..."
                  className="w-full pl-10 pr-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-600"
                />
              </div>
              <button
                onClick={handleSearch}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-300 transition-colors"
                tabIndex={0}
              >
                Search
              </button>
              {searchTerm && (
                <button
                  onClick={() => {
                    setSearchInput("")
                    setSearchTerm("")
                    setPage(1)
                  }}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-300 transition-colors"
                  tabIndex={0}
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-400"></div>
              <p className="mt-4 text-gray-400">Loading data...</p>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-4 text-red-300">
              <p className="font-medium">Error loading data</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          )}

          {/* Data Table */}
          {!loading && !error && data.length > 0 && (
            <>
              <div className="overflow-x-auto mb-4">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="bg-gray-800/50 border-b border-gray-700">
                      {columns.map((col) => (
                        <th
                          key={col}
                          className="px-4 py-3 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider"
                        >
                          {col.replace(/_/g, " ")}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((row, idx) => (
                      <tr
                        key={idx}
                        className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors"
                      >
                        {columns.map((col) => (
                          <td
                            key={col}
                            className="px-4 py-3 text-sm text-gray-300 whitespace-nowrap"
                          >
                            {formatValue(row[col], col)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {pagination && (
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-800/50">
                  <div className="text-sm text-gray-400">
                    Showing{" "}
                    <span className="font-medium text-gray-300">
                      {(pagination.page - 1) * pagination.limit + 1}
                    </span>{" "}
                    to{" "}
                    <span className="font-medium text-gray-300">
                      {Math.min(pagination.page * pagination.limit, pagination.total_rows)}
                    </span>{" "}
                    of{" "}
                    <span className="font-medium text-gray-300">
                      {pagination.total_rows.toLocaleString()}
                    </span>{" "}
                    rows
                  </div>

                  <div className="flex items-center gap-2">
                    <select
                      value={limit}
                      onChange={(e) => {
                        setLimit(parseInt(e.target.value))
                        setPage(1)
                      }}
                      className="px-3 py-1 bg-gray-800/50 border border-gray-700 rounded text-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-gray-600"
                    >
                      <option value={25}>25 per page</option>
                      <option value={50}>50 per page</option>
                      <option value={100}>100 per page</option>
                      <option value={200}>200 per page</option>
                    </select>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={!pagination.has_prev}
                        className="p-2 bg-gray-800/50 border border-gray-700 rounded text-gray-300 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        tabIndex={0}
                      >
                        <FiChevronLeft className="h-4 w-4" />
                      </button>
                      
                      <span className="px-4 py-2 text-sm text-gray-300">
                        Page {pagination.page} of {pagination.total_pages}
                      </span>
                      
                      <button
                        onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
                        disabled={!pagination.has_next}
                        className="p-2 bg-gray-800/50 border border-gray-700 rounded text-gray-300 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        tabIndex={0}
                      >
                        <FiChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Empty State */}
          {!loading && !error && data.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-400">
                {searchTerm ? "No results found for your search" : "No data available"}
              </p>
            </div>
          )}
        </div>
      )}

      {/* No File Selected */}
      {!activeFile && (
        <div className="p-12 text-center">
          <p className="text-gray-400">Select a file to view data</p>
        </div>
      )}
    </div>
  )
}

export default DataViewer

