import { useState, useEffect } from "react"
import { FiRefreshCw, FiDownload, FiCheckCircle, FiAlertCircle, FiClock, FiDatabase, FiCpu, FiActivity } from "react-icons/fi"
import ReactMarkdown from 'react-markdown'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

const SystemReport = () => {
  const [report, setReport] = useState(null)
  const [stats, setStats] = useState(null)
  const [logs, setLogs] = useState(null)
  const [testResults, setTestResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState("report") // report, stats, logs, tests

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    setLoading(true)
    await Promise.all([
      loadReport(),
      loadStats(),
      loadLogs(),
      loadTestResults()
    ])
    setLoading(false)
  }

  const loadReport = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/system/report`)
      const data = await response.json()
      if (data.success) {
        setReport(data)
      }
    } catch (error) {
      console.error("Error loading report:", error)
    }
  }

  const loadStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/system/stats`)
      const data = await response.json()
      if (data.success) {
        setStats(data)
      }
    } catch (error) {
      console.error("Error loading stats:", error)
    }
  }

  const loadLogs = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/system/logs?lines=100`)
      const data = await response.json()
      if (data.success) {
        setLogs(data)
      }
    } catch (error) {
      console.error("Error loading logs:", error)
    }
  }

  const loadTestResults = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/testing/results`)
      const data = await response.json()
      if (data.success) {
        setTestResults(data.results)
      }
    } catch (error) {
      console.error("Error loading test results:", error)
    }
  }

  const runTests = async (provider = "gemini") => {
    try {
      const response = await fetch(`${API_BASE_URL}/testing/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider })
      })
      const data = await response.json()
      if (data.success) {
        alert(`Tests started with ${provider}. Check back in a few minutes for results.`)
        setTimeout(loadTestResults, 5000) // Reload after 5 seconds
      }
    } catch (error) {
      console.error("Error running tests:", error)
      alert("Failed to start tests")
    }
  }

  const downloadReport = () => {
    if (!report) return
    const blob = new Blob([report.content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'system-report.md'
    a.click()
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">System Report & Logs</h1>
            <p className="text-gray-400">Complete system documentation, statistics, and testing</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={loadAll}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white rounded-lg transition-colors flex items-center gap-2"
            >
              <FiRefreshCw className={loading ? "animate-spin" : ""} />
              Refresh
            </button>
            {report && (
              <button
                onClick={downloadReport}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors flex items-center gap-2"
              >
                <FiDownload />
                Download
              </button>
            )}
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <FiDatabase className="text-blue-400 text-2xl" />
                <div>
                  <p className="text-sm text-gray-400">Files Uploaded</p>
                  <p className="text-2xl font-bold text-white">{stats.files.uploaded}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <FiCpu className="text-green-400 text-2xl" />
                <div>
                  <p className="text-sm text-gray-400">Agent Status</p>
                  <p className="text-lg font-bold text-white">
                    {stats.agent.gemini.available ? "✅ Gemini" : "❌ Gemini"}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <FiActivity className="text-purple-400 text-2xl" />
                <div>
                  <p className="text-sm text-gray-400">Test Success Rate</p>
                  <p className="text-2xl font-bold text-white">
                    {stats.testing?.success_rate ? `${stats.testing.success_rate}%` : "N/A"}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <FiClock className="text-yellow-400 text-2xl" />
                <div>
                  <p className="text-sm text-gray-400">Version</p>
                  <p className="text-2xl font-bold text-white">{stats.version}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl overflow-hidden">
          <div className="flex border-b border-gray-800/50">
            {[
              { id: "report", label: "System Report", icon: FiCheckCircle },
              { id: "stats", label: "Statistics", icon: FiActivity },
              { id: "tests", label: "Test Results", icon: FiCheckCircle },
              { id: "logs", label: "System Logs", icon: FiAlertCircle }
            ].map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 px-6 py-4 font-medium transition-colors flex items-center justify-center gap-2 ${
                    activeTab === tab.id
                      ? "bg-blue-600/20 text-blue-400 border-b-2 border-blue-500"
                      : "text-gray-400 hover:text-white hover:bg-gray-800/50"
                  }`}
                >
                  <Icon />
                  {tab.label}
                </button>
              )
            })}
          </div>

          <div className="p-6">
            {/* System Report Tab */}
            {activeTab === "report" && (
              <div className="prose prose-invert max-w-none">
                {loading ? (
                  <div className="flex items-center justify-center py-12">
                    <FiRefreshCw className="animate-spin text-4xl text-blue-400" />
                  </div>
                ) : report ? (
                  <div className="bg-gray-800/30 rounded-lg p-6 overflow-auto max-h-[600px]">
                    <ReactMarkdown className="markdown-content">
                      {report.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-gray-400">No report available</p>
                )}
              </div>
            )}

            {/* Statistics Tab */}
            {activeTab === "stats" && stats && (
              <div className="space-y-4">
                <div className="bg-gray-800/30 rounded-lg p-4">
                  <h3 className="text-lg font-bold mb-3">Agent Status</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-400">Gemini</p>
                      <p className={`font-medium ${stats.agent.gemini.available ? "text-green-400" : "text-red-400"}`}>
                        {stats.agent.gemini.available ? "✅ Available" : "❌ Unavailable"}
                      </p>
                      {stats.agent.gemini.model && (
                        <p className="text-xs text-gray-500">{stats.agent.gemini.model}</p>
                      )}
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Groq</p>
                      <p className={`font-medium ${stats.agent.groq.available ? "text-green-400" : "text-red-400"}`}>
                        {stats.agent.groq.available ? "✅ Available" : "❌ Unavailable"}
                      </p>
                      {stats.agent.groq.model && (
                        <p className="text-xs text-gray-500">{stats.agent.groq.model}</p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="bg-gray-800/30 rounded-lg p-4">
                  <h3 className="text-lg font-bold mb-3">Files</h3>
                  <p className="text-gray-300">Uploaded: {stats.files.uploaded}</p>
                  <p className="text-gray-300">With Metadata: {stats.files.with_metadata}</p>
                </div>

                {stats.testing && (
                  <div className="bg-gray-800/30 rounded-lg p-4">
                    <h3 className="text-lg font-bold mb-3">Testing</h3>
                    <p className="text-gray-300">Total Tests: {stats.testing.total}</p>
                    <p className="text-green-400">Passed: {stats.testing.passed}</p>
                    <p className="text-red-400">Failed: {stats.testing.failed}</p>
                    <p className="text-blue-400">Success Rate: {stats.testing.success_rate}%</p>
                  </div>
                )}
              </div>
            )}

            {/* Test Results Tab */}
            {activeTab === "tests" && (
              <div className="space-y-4">
                <div className="flex gap-2 mb-4">
                  <button
                    onClick={() => runTests("gemini")}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                  >
                    Run Tests (Gemini)
                  </button>
                  <button
                    onClick={() => runTests("groq")}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
                  >
                    Run Tests (Groq)
                  </button>
                </div>

                {testResults ? (
                  <div className="space-y-4">
                    <div className="bg-gray-800/30 rounded-lg p-4">
                      <h3 className="text-lg font-bold mb-2">Summary</h3>
                      <p>Provider: {testResults.provider}</p>
                      <p>Total: {testResults.summary.total}</p>
                      <p className="text-green-400">Passed: {testResults.summary.passed}</p>
                      <p className="text-red-400">Failed: {testResults.summary.failed}</p>
                      <p className="text-blue-400">Success Rate: {testResults.summary.success_rate}%</p>
                    </div>

                    <div className="bg-gray-800/30 rounded-lg p-4 max-h-96 overflow-auto">
                      <h3 className="text-lg font-bold mb-2">Results by Category</h3>
                      {Object.entries(testResults.by_category).map(([cat, data]) => (
                        <div key={cat} className="mb-2 p-2 bg-gray-900/50 rounded">
                          <p className="font-medium">{cat}</p>
                          <p className="text-sm text-gray-400">
                            {data.passed}/{data.total} passed ({((data.passed/data.total)*100).toFixed(1)}%)
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-400">No test results available. Run tests to see results.</p>
                )}
              </div>
            )}

            {/* Logs Tab */}
            {activeTab === "logs" && logs && (
              <div className="bg-gray-800/30 rounded-lg p-4">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-lg font-bold">Recent Logs ({logs.lines_returned} lines)</h3>
                  <button
                    onClick={loadLogs}
                    className="text-sm text-blue-400 hover:text-blue-300"
                  >
                    Refresh
                  </button>
                </div>
                <pre className="text-xs text-gray-300 bg-gray-900/50 p-4 rounded overflow-auto max-h-96 font-mono">
                  {logs.logs}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SystemReport

