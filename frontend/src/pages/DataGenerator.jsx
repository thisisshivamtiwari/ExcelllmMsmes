import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { FiPlay, FiRefreshCw, FiFileText, FiCheckCircle, FiAlertCircle, FiLoader, FiDatabase } from "react-icons/fi"
import DataViewer from "@/components/DataViewer"

const DataGenerator = () => {
  const [isGenerating, setIsGenerating] = useState(false)
  const [status, setStatus] = useState(null) // 'success', 'error', null
  const [message, setMessage] = useState("")
  const [output, setOutput] = useState("")
  const [generatedFiles, setGeneratedFiles] = useState({})
  const [existingFiles, setExistingFiles] = useState({})
  const [pythonStatus, setPythonStatus] = useState(null)

  // Form state
  const [productionRows, setProductionRows] = useState(200)
  const [qcRows, setQcRows] = useState(150)
  const [maintenanceRows, setMaintenanceRows] = useState(50)
  const [inventoryRows, setInventoryRows] = useState(100)
  const [noContinue, setNoContinue] = useState(false)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  // Fetch existing files and Python status on mount
  useEffect(() => {
    fetchExistingFiles()
    fetchPythonStatus()
  }, [])

  const fetchPythonStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/python-status`)
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`)
      }
      const data = await response.json()
      console.log("Python status response:", data) // Debug log
      setPythonStatus(data)
    } catch (error) {
      console.error("Error fetching Python status:", error)
      // Set a default status showing the error
      setPythonStatus({
        python_path: "unknown",
        python_version: "unknown",
        has_required_packages: false,
        status: "error",
        message: `Failed to connect to backend: ${error.message}. Make sure the backend server is running on port 8000.`,
      })
    }
  }

  const fetchExistingFiles = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/files`)
      const data = await response.json()
      setExistingFiles(data.files || {})
    } catch (error) {
      console.error("Error fetching files:", error)
    }
  }

  const handleGenerate = async () => {
    setIsGenerating(true)
    setStatus(null)
    setMessage("")
    setOutput("")
    setGeneratedFiles({})

    try {
      const response = await fetch(`${API_BASE_URL}/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          production_rows: productionRows,
          qc_rows: qcRows,
          maintenance_rows: maintenanceRows,
          inventory_rows: inventoryRows,
          no_continue: noContinue,
        }),
      })

      const data = await response.json()

      if (data.status === "success") {
        setStatus("success")
        setMessage(data.message || "Data generation completed successfully")
        setOutput(data.output || "")
        setGeneratedFiles(data.files || {})
        // Refresh existing files list
        await fetchExistingFiles()
      } else {
        setStatus("error")
        setMessage(data.message || "Data generation failed")
        setOutput(data.output || "")
      }
    } catch (error) {
      setStatus("error")
      setMessage(`Error: ${error.message}`)
      setOutput("")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !isGenerating) {
      handleGenerate()
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
          <h1 className="text-3xl font-bold text-gray-100 mb-2">Data Generator</h1>
          <p className="text-gray-400">
            Generate realistic MSME shopfloor manufacturing data using Google Gemini API
          </p>
        </div>

        {/* Python Environment Status */}
        {pythonStatus ? (
          <div
            className={`mb-6 p-4 rounded-lg border ${
              pythonStatus.status === "ready"
                ? "bg-green-900/20 border-green-700/50"
                : pythonStatus.status === "error"
                ? "bg-red-900/20 border-red-700/50"
                : "bg-yellow-900/20 border-yellow-700/50"
            }`}
          >
            <div className="flex items-start gap-3">
              {pythonStatus.status === "ready" ? (
                <FiCheckCircle className="h-5 w-5 text-green-400 mt-0.5 shrink-0" />
              ) : (
                <FiAlertCircle
                  className={`h-5 w-5 mt-0.5 shrink-0 ${
                    pythonStatus.status === "error" ? "text-red-400" : "text-yellow-400"
                  }`}
                />
              )}
              <div className="flex-1">
                <p
                  className={`font-medium mb-1 ${
                    pythonStatus.status === "ready"
                      ? "text-green-300"
                      : pythonStatus.status === "error"
                      ? "text-red-300"
                      : "text-yellow-300"
                  }`}
                >
                  Python Environment Status
                </p>
                <p className="text-sm text-gray-300 mb-2">
                  Python: <span className="font-mono">{pythonStatus.python_path || "unknown"}</span>
                  {pythonStatus.python_version && 
                   pythonStatus.python_version !== "unknown" && 
                   !pythonStatus.python_version.startsWith("error") && (
                    <span> ({pythonStatus.python_version})</span>
                  )}
                </p>
                {pythonStatus.status !== "ready" && (
                  <div className="mt-2 p-3 bg-gray-950/50 rounded border border-gray-700">
                    <p
                      className={`text-sm mb-2 font-medium ${
                        pythonStatus.status === "error" ? "text-red-300" : "text-yellow-300"
                      }`}
                    >
                      {pythonStatus.status === "error"
                        ? "Error"
                        : pythonStatus.missing_packages?.length > 0
                        ? `Missing Packages: ${pythonStatus.missing_packages.join(", ")}`
                        : "Missing Required Packages"}
                    </p>
                    <p className="text-xs text-gray-400 font-mono mb-2 whitespace-pre-wrap">
                      {pythonStatus.message || "Unable to determine status"}
                    </p>
                    {pythonStatus.status !== "error" && (
                      <p className="text-xs text-gray-500">
                        After installing packages, refresh this page to verify.
                      </p>
                    )}
                    {pythonStatus.status === "error" && pythonStatus.message?.includes("backend") && (
                      <p className="text-xs text-gray-500 mt-2">
                        Make sure the backend server is running: <code className="bg-gray-900 px-1 rounded">cd backend && python main.py</code>
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="mb-6 p-4 rounded-lg border bg-gray-900/20 border-gray-700/50">
            <div className="flex items-center gap-2">
              <FiLoader className="h-5 w-5 text-gray-400 animate-spin" />
              <p className="text-gray-400">Checking Python environment...</p>
            </div>
          </div>
        )}

        {/* Configuration Card */}
        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mb-6">
          <h2 className="text-xl font-semibold text-gray-100 mb-4">Configuration</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Production Logs (rows)
              </label>
              <input
                type="number"
                value={productionRows}
                onChange={(e) => setProductionRows(parseInt(e.target.value) || 0)}
                className="w-full px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-600"
                min="0"
                disabled={isGenerating}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                QC Entries (rows)
              </label>
              <input
                type="number"
                value={qcRows}
                onChange={(e) => setQcRows(parseInt(e.target.value) || 0)}
                className="w-full px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-600"
                min="0"
                disabled={isGenerating}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Maintenance Logs (rows)
              </label>
              <input
                type="number"
                value={maintenanceRows}
                onChange={(e) => setMaintenanceRows(parseInt(e.target.value) || 0)}
                className="w-full px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-600"
                min="0"
                disabled={isGenerating}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Inventory Logs (rows)
              </label>
              <input
                type="number"
                value={inventoryRows}
                onChange={(e) => setInventoryRows(parseInt(e.target.value) || 0)}
                className="w-full px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-600"
                min="0"
                disabled={isGenerating}
              />
            </div>
          </div>

          <div className="flex items-center gap-2 mb-6">
            <input
              type="checkbox"
              id="no-continue"
              checked={noContinue}
              onChange={(e) => setNoContinue(e.target.checked)}
              className="w-4 h-4 rounded border-gray-700 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-gray-600"
              disabled={isGenerating}
            />
            <label htmlFor="no-continue" className="text-sm text-gray-300 cursor-pointer">
              Start fresh (don't continue from existing files)
            </label>
          </div>

          <Button
            onClick={handleGenerate}
            onKeyDown={handleKeyDown}
            disabled={isGenerating || (pythonStatus && !pythonStatus.has_required_packages)}
            className="w-full md:w-auto"
            tabIndex={0}
          >
            {isGenerating ? (
              <>
                <FiLoader className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <FiPlay className="h-4 w-4 mr-2" />
                Generate Data
              </>
            )}
          </Button>
        </div>

        {/* Status Message */}
        {status && (
          <div
            className={`mb-6 p-4 rounded-lg border ${
              status === "success"
                ? "bg-green-900/20 border-green-700/50 text-green-300"
                : "bg-red-900/20 border-red-700/50 text-red-300"
            }`}
          >
            <div className="flex items-start gap-2">
              {status === "success" ? (
                <FiCheckCircle className="h-5 w-5 mt-0.5 shrink-0" />
              ) : (
                <FiAlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
              )}
              <div className="flex-1">
                <span className="font-medium">{message}</span>
                {status === "error" && output && (
                  <pre className="mt-2 text-xs bg-gray-950/50 p-3 rounded overflow-x-auto font-mono whitespace-pre-wrap">
                    {output}
                  </pre>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Generated Files */}
        {status === "success" && Object.keys(generatedFiles).length > 0 && (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mb-6">
            <h2 className="text-xl font-semibold text-gray-100 mb-4 flex items-center gap-2">
              <FiFileText className="h-5 w-5" />
              Generated Files
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(generatedFiles).map(([fileName, rowCount]) => (
                <div
                  key={fileName}
                  className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300 font-medium">{fileName}</span>
                    <span className="text-gray-400 text-sm">{rowCount} rows</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Existing Files */}
        {Object.keys(existingFiles).length > 0 && (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-100 flex items-center gap-2">
                <FiFileText className="h-5 w-5" />
                Existing Files
              </h2>
              <button
                onClick={fetchExistingFiles}
                className="text-gray-400 hover:text-gray-100 transition-colors"
                tabIndex={0}
              >
                <FiRefreshCw className="h-5 w-5" />
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(existingFiles).map(([fileName, fileInfo]) => {
                if (!fileInfo.exists) return null
                return (
                  <div
                    key={fileName}
                    className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-gray-300 font-medium">{fileName}</span>
                      <span className="text-gray-400 text-sm">
                        {fileInfo.rows || 0} rows
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Data Viewer */}
        {availableFiles.length > 0 && (
          <div className="mt-8">
            <div className="mb-4">
              <h2 className="text-2xl font-bold text-gray-100 mb-2 flex items-center gap-2">
                <FiDatabase className="h-6 w-6" />
                View Generated Data
              </h2>
              <p className="text-gray-400">
                Browse and search through all generated data files in detail
              </p>
            </div>
            <DataViewer fileNames={availableFiles} API_BASE_URL={API_BASE_URL} />
          </div>
        )}

        {/* Output Log */}
        {output && (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mt-6">
            <h2 className="text-xl font-semibold text-gray-100 mb-4">Output Log</h2>
            <pre className="bg-gray-950/50 p-4 rounded-lg overflow-x-auto text-sm text-gray-300 font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
              {output}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default DataGenerator

