import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { FiPlay, FiRefreshCw, FiCode, FiCheckCircle, FiAlertCircle, FiLoader } from "react-icons/fi"
import PromptOptimizationVisualizations from "@/components/PromptOptimizationVisualizations"
import VisualizationImages from "@/components/VisualizationImages"

const PromptEngineering = () => {
  const [isTesting, setIsTesting] = useState(false)
  const [status, setStatus] = useState(null)
  const [message, setMessage] = useState("")
  const [output, setOutput] = useState("")
  const [results, setResults] = useState(null)
  const [visualizationImages, setVisualizationImages] = useState([])
  const [loadingVisualizations, setLoadingVisualizations] = useState(false)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  useEffect(() => {
    fetchResults()
    fetchVisualizations()
  }, [])

  const fetchVisualizations = async () => {
    setLoadingVisualizations(true)
    try {
      const response = await fetch(`${API_BASE_URL}/visualizations/prompt-engineering/list`)
      if (response.ok) {
        const data = await response.json()
        console.log("Prompt engineering visualizations:", data)
        setVisualizationImages(data.images || [])
      } else {
        console.warn(`Failed to fetch visualizations: ${response.status} ${response.statusText}`)
        setVisualizationImages([])
      }
    } catch (error) {
      console.error("Error fetching visualizations:", error)
      setVisualizationImages([])
    } finally {
      setLoadingVisualizations(false)
    }
  }

  const fetchResults = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/prompt-engineering/results`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      // Handle both nested results and direct structure
      if (data.results && Object.keys(data.results).length > 0) {
        setResults(data.results)
      } else if (data.report || data.detailed_results) {
        setResults(data)
      } else {
        setResults(null)
      }
    } catch (error) {
      console.error("Error fetching results:", error)
      setResults(null)
    }
  }

  const handleTestPrompts = async () => {
    setIsTesting(true)
    setStatus(null)
    setMessage("")
    setOutput("")

    try {
      const response = await fetch(`${API_BASE_URL}/prompt-engineering/test`, {
        method: "POST",
      })

      const data = await response.json()

      if (data.status === "success") {
        setStatus("success")
        setMessage(data.message)
        setOutput(data.output || "")
        // Handle both nested results and direct structure
        if (data.results && Object.keys(data.results).length > 0) {
          setResults(data.results)
        } else if (data.report || data.detailed_results) {
          setResults(data)
        } else {
          setResults(null)
        }
        fetchVisualizations() // Refresh visualizations after running
      } else {
        setStatus("error")
        setMessage(data.message || "Prompt testing failed")
        setOutput(data.output || "")
      }
    } catch (error) {
      setStatus("error")
      setMessage(`Error: ${error.message}`)
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-100 mb-2 flex items-center gap-2">
            <FiCode className="h-8 w-8" />
            Model Optimization
          </h1>
          <p className="text-gray-400">
            Compare enhanced prompts against baseline performance for Llama 4 Maverick to improve accuracy on MSME manufacturing questions
          </p>
        </div>

        {/* Test Button */}
        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-100 mb-2">Test Enhanced Prompts</h2>
              <p className="text-sm text-gray-400">
                Compares enhanced prompts against baseline performance to optimize model accuracy
              </p>
            </div>
            <Button
              onClick={handleTestPrompts}
              disabled={isTesting}
              className="shrink-0"
            >
              {isTesting ? (
                <>
                  <FiLoader className="h-4 w-4 mr-2 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  <FiPlay className="h-4 w-4 mr-2" />
                  Test Prompts
                </>
              )}
            </Button>
          </div>
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

        {/* Results Display with Visualizations */}
        {results && Object.keys(results).length > 0 ? (
          <div className="space-y-6">
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-100">Optimization Results</h2>
                <button
                  onClick={fetchResults}
                  className="text-gray-400 hover:text-gray-100 transition-colors"
                  tabIndex={0}
                >
                  <FiRefreshCw className="h-5 w-5" />
                </button>
              </div>
            </div>
            <PromptOptimizationVisualizations results={results} />
            <VisualizationImages
              images={visualizationImages}
              title="Saved Visualizations"
              loading={loadingVisualizations}
            />
          </div>
        ) : (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
            <div className="text-center py-8 text-gray-400">
              <p>No model optimization results found.</p>
              <p className="text-sm mt-2">Test enhanced prompts to see visualizations here.</p>
            </div>
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

export default PromptEngineering

