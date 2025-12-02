import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { FiPlay, FiRefreshCw, FiBarChart2, FiCheckCircle, FiAlertCircle, FiLoader } from "react-icons/fi"
import BenchmarkVisualizations from "@/components/BenchmarkVisualizations"
import VisualizationImages from "@/components/VisualizationImages"

const Benchmarking = () => {
  const [isRunning, setIsRunning] = useState(false)
  const [status, setStatus] = useState(null)
  const [message, setMessage] = useState("")
  const [output, setOutput] = useState("")
  const [results, setResults] = useState(null)

  // Configuration
  const [sampleSize, setSampleSize] = useState(30)
  const [selectedCategories, setSelectedCategories] = useState(["Easy", "Medium", "Complex"])
  const [useGemini, setUseGemini] = useState(true)
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
      const response = await fetch(`${API_BASE_URL}/visualizations/benchmark/list`)
      if (response.ok) {
        const data = await response.json()
        console.log("Benchmark visualizations:", data)
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
      const response = await fetch(`${API_BASE_URL}/benchmark/results`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      if (data.results && Object.keys(data.results).length > 0) {
        setResults(data.results)
      } else if (data.message) {
        // Results file doesn't exist yet
        setResults(null)
      }
    } catch (error) {
      console.error("Error fetching results:", error)
      setResults(null)
    }
  }

  const handleRunBenchmark = async () => {
    setIsRunning(true)
    setStatus(null)
    setMessage("")
    setOutput("")

    try {
      const response = await fetch(`${API_BASE_URL}/benchmark/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sample_size: sampleSize,
          categories: selectedCategories,
          use_gemini: useGemini,
        }),
      })

      const data = await response.json()

      if (data.status === "success") {
        setStatus("success")
        setMessage(data.message)
        setOutput(data.output || "")
        setResults(data.results || null)
        fetchVisualizations() // Refresh visualizations after running
      } else {
        setStatus("error")
        setMessage(data.message || "Benchmark failed")
        setOutput(data.output || "")
      }
    } catch (error) {
      setStatus("error")
      setMessage(`Error: ${error.message}`)
    } finally {
      setIsRunning(false)
    }
  }

  const toggleCategory = (category) => {
    setSelectedCategories((prev) =>
      prev.includes(category)
        ? prev.filter((c) => c !== category)
        : [...prev, category]
    )
  }

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-100 mb-2 flex items-center gap-2">
            <FiBarChart2 className="h-8 w-8" />
            LLM Benchmarking
          </h1>
          <p className="text-gray-400">
            Evaluate LLM performance on MSME manufacturing questions using hybrid evaluation approach
          </p>
        </div>

        {/* Configuration */}
        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mb-6">
          <h2 className="text-xl font-semibold text-gray-100 mb-4">Configuration</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Sample Size (number of questions)
              </label>
              <input
                type="number"
                value={sampleSize}
                onChange={(e) => setSampleSize(parseInt(e.target.value) || 0)}
                className="w-full md:w-64 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-600"
                min="1"
                disabled={isRunning}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Question Categories
              </label>
              <div className="flex flex-wrap gap-2">
                {["Easy", "Medium", "Complex"].map((cat) => (
                  <button
                    key={cat}
                    onClick={() => toggleCategory(cat)}
                    disabled={isRunning}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedCategories.includes(cat)
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800/50 text-gray-300 hover:bg-gray-700"
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="use-gemini"
                checked={useGemini}
                onChange={(e) => setUseGemini(e.target.checked)}
                className="w-4 h-4 rounded border-gray-700 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-gray-600"
                disabled={isRunning}
              />
              <label htmlFor="use-gemini" className="text-sm text-gray-300 cursor-pointer">
                Use Gemini for methodology evaluation (more accurate but slower)
              </label>
            </div>

            <Button
              onClick={handleRunBenchmark}
              disabled={isRunning}
              className="w-full md:w-auto"
            >
              {isRunning ? (
                <>
                  <FiLoader className="h-4 w-4 mr-2 animate-spin" />
                  Running Benchmark...
                </>
              ) : (
                <>
                  <FiPlay className="h-4 w-4 mr-2" />
                  Run Benchmark
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
        <div className="space-y-6">
          {results && Object.keys(results).length > 0 ? (
            <>
              <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-100">Benchmark Results</h2>
                  <button
                    onClick={fetchResults}
                    className="text-gray-400 hover:text-gray-100 transition-colors"
                    tabIndex={0}
                  >
                    <FiRefreshCw className="h-5 w-5" />
                  </button>
                </div>
              </div>
              <BenchmarkVisualizations results={results} />
            </>
          ) : (
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
              <div className="text-center py-8 text-gray-400">
                <p>No benchmark results found.</p>
                <p className="text-sm mt-2">Run a benchmark to see results here.</p>
              </div>
            </div>
          )}
          
          {/* Always show saved visualizations if they exist */}
          <VisualizationImages
            images={visualizationImages}
            title="Saved Visualizations"
            loading={loadingVisualizations}
          />
        </div>

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

export default Benchmarking

