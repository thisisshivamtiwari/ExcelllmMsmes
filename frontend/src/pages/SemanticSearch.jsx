import { useState, useEffect } from "react"
import { FiSearch, FiLoader, FiDatabase, FiLink, FiFile, FiBarChart2, FiTrendingUp, FiRefreshCw, FiInfo, FiCheckCircle, FiAlertCircle } from "react-icons/fi"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/contexts/AuthContext"

const SemanticSearch = () => {
  const { token } = useAuth()
  const [query, setQuery] = useState("")
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState("all")
  const [nResults, setNResults] = useState(10)
  const [indexing, setIndexing] = useState(false)
  const [indexStats, setIndexStats] = useState(null)
  const [indexingAll, setIndexingAll] = useState(false)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  // Load files and stats on mount
  useEffect(() => {
    fetchFiles()
    fetchIndexStats()
  }, [token])

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
      } else if (response.status === 401) {
        console.error("Unauthorized - please login")
      }
    } catch (error) {
      console.error("Error fetching files:", error)
    }
  }

  const fetchIndexStats = async () => {
    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const response = await fetch(`${API_BASE_URL}/semantic/stats`, { headers })
      if (response.ok) {
        const data = await response.json()
        setIndexStats(data)
      } else if (response.status === 401) {
        setIndexStats({ available: false, message: "Please login to use semantic search" })
      } else {
        const errorData = await response.json().catch(() => ({}))
        setIndexStats({ available: false, message: errorData.detail || "Vector store not initialized" })
      }
    } catch (error) {
      setIndexStats({ available: false, message: "Error loading vector store stats" })
    }
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) {
      setError("Please enter a search query")
      return
    }

    setSearching(true)
    setError(null)
    setResults(null)

    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const fileFilter = selectedFile !== "all" ? selectedFile : undefined
      const url = new URL(`${API_BASE_URL}/semantic/search`)
      url.searchParams.append("query", query.trim())
      url.searchParams.append("n_results", nResults.toString())
      if (fileFilter) {
        url.searchParams.append("file_id", fileFilter)
      }

      const response = await fetch(url.toString(), {
        method: "POST",
        headers
      })

      if (response.ok) {
        const data = await response.json()
        setResults(data)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || "Search failed")
      }
    } catch (error) {
      setError(`Error: ${error.message}`)
    } finally {
      setSearching(false)
    }
  }

  const handleIndexFile = async (fileId) => {
    setIndexing(true)
    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const response = await fetch(`${API_BASE_URL}/semantic/index/${fileId}`, {
        method: "POST",
        headers
      })

      if (response.ok) {
        const data = await response.json()
        alert(data.message || "File indexed successfully")
        await fetchIndexStats()
      } else {
        const errorData = await response.json()
        alert(errorData.detail || "Indexing failed")
      }
    } catch (error) {
      alert(`Error: ${error.message}`)
    } finally {
      setIndexing(false)
    }
  }

  const handleIndexAll = async () => {
    setIndexingAll(true)
    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const response = await fetch(`${API_BASE_URL}/semantic/index-all`, {
        method: "POST",
        headers
      })

      if (response.ok) {
        const data = await response.json()
        alert(data.message || `Indexed ${data.indexed} files`)
        await fetchIndexStats()
      } else {
        const errorData = await response.json()
        alert(errorData.detail || "Indexing failed")
      }
    } catch (error) {
      alert(`Error: ${error.message}`)
    } finally {
      setIndexingAll(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
            <FiSearch className="w-8 h-8 text-blue-400" />
            Semantic Search
          </h1>
          <p className="text-gray-400">
            Search across all your Excel files using natural language queries. Find columns, relationships, and data patterns.
          </p>
        </div>

        {/* Index Stats & Actions */}
        <div className="mb-6 p-4 rounded-lg bg-gray-900/50 border border-gray-800">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              {indexStats?.available ? (
                <div className="flex items-center gap-2 text-green-400">
                  <FiCheckCircle className="w-5 h-5" />
                  <span className="text-sm">
                    Vector store active - {indexStats.stats?.total_documents || 0} documents indexed
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-yellow-400">
                  <FiAlertCircle className="w-5 h-5" />
                  <span className="text-sm">Vector store not initialized</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={handleIndexAll}
                disabled={indexingAll}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {indexingAll ? (
                  <>
                    <FiLoader className="w-4 h-4 mr-2 animate-spin" />
                    Indexing...
                  </>
                ) : (
                  <>
                    <FiRefreshCw className="w-4 h-4 mr-2" />
                    Index All Files
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="mb-6">
          <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
            <div className="space-y-4">
              {/* Search Input */}
              <div className="relative">
                <FiSearch className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., 'production efficiency', 'defect rates', 'inventory levels'..."
                  className="w-full pl-12 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={searching}
                />
              </div>

              {/* Filters */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Filter by File
                  </label>
                  <select
                    value={selectedFile}
                    onChange={(e) => setSelectedFile(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={searching}
                  >
                    <option value="all">All Files</option>
                    {files.map((file) => (
                      <option key={file.file_id} value={file.file_id}>
                        {file.original_filename || file.filename}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Number of Results
                  </label>
                  <select
                    value={nResults}
                    onChange={(e) => setNResults(parseInt(e.target.value))}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={searching}
                  >
                    <option value={5}>5 results</option>
                    <option value={10}>10 results</option>
                    <option value={20}>20 results</option>
                    <option value={50}>50 results</option>
                  </select>
                </div>
              </div>

              {/* Search Button */}
              <Button
                type="submit"
                disabled={searching || !query.trim()}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {searching ? (
                  <>
                    <FiLoader className="w-5 h-5 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <FiSearch className="w-5 h-5 mr-2" />
                    Search
                  </>
                )}
              </Button>
            </div>
          </div>
        </form>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-900/20 border border-red-800 text-red-300 flex items-center gap-2">
            <FiAlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}

        {/* Results */}
        {results && (
          <div className="space-y-6">
            {/* Results Summary */}
            <div className="p-4 rounded-lg bg-gray-900/50 border border-gray-800">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold mb-1">Search Results</h2>
                  <p className="text-sm text-gray-400">
                    Found {results.total_columns || 0} columns and {results.total_relationships || 0} relationships
                  </p>
                </div>
                <div className="text-sm text-gray-400">
                  Query: <span className="text-gray-200 font-medium">"{results.query}"</span>
                </div>
              </div>
            </div>

            {/* Columns Results */}
            {results.results?.columns && results.results.columns.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <FiDatabase className="w-5 h-5 text-blue-400" />
                  Relevant Columns ({results.results.columns.length})
                </h3>
                <div className="space-y-3">
                  {results.results.columns.map((col, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-lg bg-gray-900/50 border border-gray-800 hover:border-gray-700 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <span className="font-semibold text-blue-400">{col.column_name}</span>
                            {col.column_type && (
                              <span className="px-2 py-1 text-xs rounded bg-gray-800 text-gray-400">
                                {col.column_type}
                              </span>
                            )}
                            {col.semantic_type && (
                              <span className="px-2 py-1 text-xs rounded bg-purple-900/30 text-purple-300">
                                {col.semantic_type}
                              </span>
                            )}
                            {col.relevance_score && (
                              <span className="px-2 py-1 text-xs rounded bg-green-900/30 text-green-300">
                                {(col.relevance_score * 100).toFixed(0)}% match
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-gray-400 mb-2">
                            <span className="text-gray-500">File:</span> {col.file_name}
                            {col.sheet_name && (
                              <>
                                {" "}• <span className="text-gray-500">Sheet:</span> {col.sheet_name}
                              </>
                            )}
                          </div>
                          {col.description && (
                            <p className="text-sm text-gray-300 mb-2">{col.description}</p>
                          )}
                          {col.user_definition && (
                            <div className="mt-2 p-2 rounded bg-gray-800/50 border border-gray-700">
                              <span className="text-xs text-gray-500">User Definition:</span>
                              <p className="text-sm text-gray-300 mt-1">{col.user_definition}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Relationships Results */}
            {results.results?.relationships && results.results.relationships.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <FiLink className="w-5 h-5 text-purple-400" />
                  Relevant Relationships ({results.results.relationships.length})
                </h3>
                <div className="space-y-3">
                  {results.results.relationships.map((rel, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-lg bg-gray-900/50 border border-gray-800 hover:border-gray-700 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2 flex-wrap">
                            <span className="px-2 py-1 text-xs font-medium rounded bg-purple-900/30 text-purple-300">
                              {rel.type?.replace(/_/g, " ") || "relationship"}
                            </span>
                            <span className="text-gray-300">
                              {rel.source_column} → {rel.target_column}
                            </span>
                            {rel.strength && (
                              <span className={`px-2 py-1 text-xs rounded ${
                                rel.strength === "strong" ? "bg-green-900/30 text-green-300" :
                                rel.strength === "medium" ? "bg-yellow-900/30 text-yellow-300" :
                                "bg-gray-700 text-gray-400"
                              }`}>
                                {rel.strength}
                              </span>
                            )}
                            {rel.relevance_score && (
                              <span className="px-2 py-1 text-xs rounded bg-green-900/30 text-green-300">
                                {(rel.relevance_score * 100).toFixed(0)}% match
                              </span>
                            )}
                          </div>
                          {rel.description && (
                            <p className="text-sm text-gray-300">{rel.description}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* No Results */}
            {(!results.results?.columns || results.results.columns.length === 0) &&
             (!results.results?.relationships || results.results.relationships.length === 0) && (
              <div className="p-8 text-center rounded-lg bg-gray-900/50 border border-gray-800">
                <FiInfo className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">No results found for your query.</p>
                <p className="text-sm text-gray-500 mt-2">
                  Try different keywords or make sure files are indexed.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Empty State */}
        {!results && !error && (
          <div className="p-12 text-center rounded-lg bg-gray-900/50 border border-gray-800">
            <FiSearch className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-300 mb-2">Start Searching</h3>
            <p className="text-gray-400 mb-6">
              Enter a natural language query to search across all indexed files.
            </p>
            <div className="flex flex-wrap justify-center gap-2 text-sm text-gray-500">
              <span className="px-3 py-1 rounded bg-gray-800">Example: "production efficiency"</span>
              <span className="px-3 py-1 rounded bg-gray-800">Example: "defect rates by product"</span>
              <span className="px-3 py-1 rounded bg-gray-800">Example: "inventory levels"</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default SemanticSearch




