import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { FiPlay, FiRefreshCw, FiFileText, FiCheckCircle, FiAlertCircle, FiLoader, FiSearch, FiFile, FiDatabase, FiShield } from "react-icons/fi"
import { useAuth } from "@/contexts/AuthContext"

const QuestionGenerator = () => {
  const { token } = useAuth()
  const [isGenerating, setIsGenerating] = useState(false)
  const [status, setStatus] = useState(null)
  const [message, setMessage] = useState("")
  const [output, setOutput] = useState("")
  const [questions, setQuestions] = useState(null)
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [selectedTable, setSelectedTable] = useState(null)
  const [numQuestions, setNumQuestions] = useState(10)
  const [questionTypes, setQuestionTypes] = useState(["factual", "aggregation", "comparative", "trend"])
  const [generateAllFiles, setGenerateAllFiles] = useState(true)  // Default to generating across all files

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  useEffect(() => {
    fetchFiles()
    fetchQuestions()
  }, [token])

  // Auto-select first category with questions when questions load
  useEffect(() => {
    if (questions && questions.questions && !selectedCategory) {
      const firstCategoryWithQuestions = categories.find(
        (cat) => questions.questions[cat] && questions.questions[cat].length > 0
      )
      if (firstCategoryWithQuestions) {
        setSelectedCategory(firstCategoryWithQuestions)
      }
    }
  }, [questions])

  // Auto-select first table when file is selected
  useEffect(() => {
    if (selectedFile && !selectedTable) {
      const file = files.find(f => f.file_id === selectedFile)
      if (file && file.sheet_names && file.sheet_names.length > 0) {
        setSelectedTable(file.sheet_names[0])
      }
    }
  }, [selectedFile, files])

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
      }
    } catch (error) {
      console.error("Error fetching files:", error)
    }
  }

  const fetchQuestions = async () => {
    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
      
      const response = await fetch(`${API_BASE_URL}/question-generator/questions?t=${Date.now()}`, {
        headers,
        cache: 'no-store'
      })
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.questions) {
          setQuestions(data)
        } else {
          setQuestions(null)
        }
      }
    } catch (error) {
      console.error("Error fetching questions:", error)
      setQuestions(null)
    }
  }

  const handleGenerate = async () => {
    if (!generateAllFiles && !selectedFile) {
      setStatus("error")
      setMessage("Please select a file first or enable 'Generate Across All Files'")
      return
    }

    setIsGenerating(true)
    setStatus(null)
    setMessage("")
    setOutput("")

    try {
      const headers = {
        "Content-Type": "application/json"
      }
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }

      const requestBody = {
        question_types: questionTypes,
        num_questions: numQuestions,
        generate_all_files: generateAllFiles
      }

      // Only include file_id and table_name if generating for a specific file
      if (!generateAllFiles && selectedFile) {
        requestBody.file_id = selectedFile
        if (selectedTable) {
          requestBody.table_name = selectedTable
        }
      }

      const response = await fetch(`${API_BASE_URL}/question-generator/generate`, {
        method: "POST",
        headers,
        body: JSON.stringify(requestBody)
      })

      const data = await response.json()

      if (data.status === "success") {
        setStatus("success")
        setMessage(data.message)
        setOutput(JSON.stringify(data.result, null, 2))
        // Refresh questions after generation
        setTimeout(() => fetchQuestions(), 1000)
      } else {
        setStatus("error")
        setMessage(data.detail || data.message || "Question generation failed")
        setOutput(JSON.stringify(data, null, 2))
      }
    } catch (error) {
      setStatus("error")
      setMessage(`Error: ${error.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleVerifyAll = async () => {
    setIsGenerating(true)
    setStatus(null)
    setMessage("")

    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }

      const response = await fetch(`${API_BASE_URL}/question-generator/verify-all`, {
        method: "POST",
        headers
      })

      const data = await response.json()

      if (data.success) {
        setStatus("success")
        let message = data.message || `Verified ${data.verified} questions, ${data.still_unverified} still unverified`
        
        // Add error details if available
        if (data.error_details && data.error_details.length > 0) {
          message += `\n\nFirst few errors:\n${data.error_details.slice(0, 3).map((e, i) => 
            `${i + 1}. ${e.question}: Expected ${e.expected}, Got ${e.computed} (${e.error})`
          ).join('\n')}`
        }
        
        // Check if data needs normalization
        if (data.tables_count === 0) {
          message += "\n\n⚠️ No normalized data found. Please click 'Normalize Data' first."
        }
        
        setMessage(message)
        setOutput(JSON.stringify(data, null, 2))
        // Refresh questions after verification
        setTimeout(() => fetchQuestions(), 1000)
      } else {
        setStatus("error")
        setMessage(data.detail || data.message || "Verification failed")
        setOutput(JSON.stringify(data, null, 2))
      }
    } catch (error) {
      setStatus("error")
      setMessage(`Error: ${error.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleNormalize = async () => {
    if (!selectedFile) {
      setStatus("error")
      setMessage("Please select a file first")
      return
    }

    setIsGenerating(true)
    setStatus(null)
    setMessage("")

    try {
      const headers = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }

      const response = await fetch(`${API_BASE_URL}/question-generator/normalize/${selectedFile}`, {
        method: "POST",
        headers
      })

      const data = await response.json()

      if (data.status === "success") {
        setStatus("success")
        setMessage(data.message)
      } else {
        setStatus("error")
        setMessage(data.detail || data.message || "Normalization failed")
      }
    } catch (error) {
      setStatus("error")
      setMessage(`Error: ${error.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const categories = ["Easy", "Medium", "Hard"]
  const questionCounts = questions?.metadata?.questions_by_category || {}

  const filteredQuestions = selectedCategory && questions?.questions?.[selectedCategory]
    ? questions.questions[selectedCategory].filter((q) =>
        searchTerm
          ? q.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
            q.answer?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            q.explanation?.toLowerCase().includes(searchTerm.toLowerCase())
          : true
      )
    : []

  const selectedFileData = files.find(f => f.file_id === selectedFile)

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-100 mb-2 flex items-center gap-2">
            <FiFileText className="h-8 w-8" />
            MongoDB Question Generator
          </h1>
          <p className="text-gray-400">
            Generate verified questions from your MongoDB data with automatic answer verification
          </p>
        </div>

        {/* File Selection & Configuration */}
        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg mb-6">
          <h2 className="text-xl font-semibold text-gray-100 mb-4">Configuration</h2>
          
          <div className="space-y-4">
            {/* Generate Across All Files Toggle */}
            <div className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg border border-gray-700">
              <input
                type="checkbox"
                id="generateAllFiles"
                checked={generateAllFiles}
                onChange={(e) => {
                  setGenerateAllFiles(e.target.checked)
                  if (e.target.checked) {
                    setSelectedFile(null)
                    setSelectedTable(null)
                  }
                }}
                className="w-5 h-5 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                disabled={isGenerating}
              />
              <label htmlFor="generateAllFiles" className="text-sm font-medium text-gray-300 cursor-pointer">
                Generate questions across ALL uploaded files
              </label>
            </div>

            {/* File Selection (only if not generating all files) */}
            {!generateAllFiles && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Select File
                  </label>
                  <select
                    value={selectedFile || ""}
                    onChange={(e) => {
                      setSelectedFile(e.target.value)
                      setSelectedTable(null)
                    }}
                    className="w-full px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-600"
                    disabled={isGenerating}
                  >
                    <option value="">-- Select a file --</option>
                    {files.map((file) => (
                      <option key={file.file_id} value={file.file_id}>
                        {file.filename || file.original_filename} ({file.file_type?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>
              </>
            )}

            {/* Table Selection (only if not generating all files) */}
            {!generateAllFiles && selectedFileData && selectedFileData.sheet_names && selectedFileData.sheet_names.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Select Table/Sheet
                </label>
                <select
                  value={selectedTable || ""}
                  onChange={(e) => setSelectedTable(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-600"
                  disabled={isGenerating}
                >
                  <option value="">-- Select a table --</option>
                  {selectedFileData.sheet_names.map((sheet) => (
                    <option key={sheet} value={sheet}>
                      {sheet}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Number of Questions */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Number of Questions {generateAllFiles ? "per File" : ""}
              </label>
              <input
                type="number"
                value={numQuestions}
                onChange={(e) => setNumQuestions(parseInt(e.target.value) || 10)}
                className="w-full md:w-64 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-600"
                min="1"
                max="100"
                disabled={isGenerating}
              />
              {generateAllFiles && (
                <p className="text-xs text-gray-500 mt-1">
                  {files.length} files × {numQuestions} questions = ~{files.length * numQuestions} total questions
                </p>
              )}
            </div>

            {/* Question Types */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Question Types
              </label>
              <div className="flex flex-wrap gap-2">
                {["factual", "aggregation", "comparative", "trend", "mcq", "anomaly"].map((type) => (
                  <button
                    key={type}
                    onClick={() => {
                      if (questionTypes.includes(type)) {
                        setQuestionTypes(questionTypes.filter(t => t !== type))
                      } else {
                        setQuestionTypes([...questionTypes, type])
                      }
                    }}
                    disabled={isGenerating}
                    className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                      questionTypes.includes(type)
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800/50 text-gray-300 hover:bg-gray-700"
                    }`}
                  >
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-2 pt-2">
              {!generateAllFiles && (
                <Button
                  onClick={handleNormalize}
                  disabled={isGenerating || !selectedFile}
                  className="bg-gray-700 hover:bg-gray-600"
                >
                  <FiDatabase className="h-4 w-4 mr-2" />
                  Normalize Data
                </Button>
              )}
              <Button
                onClick={handleGenerate}
                disabled={isGenerating || (generateAllFiles && files.length === 0)}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isGenerating ? (
                  <>
                    <FiLoader className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <FiPlay className="h-4 w-4 mr-2" />
                    Generate Questions
                  </>
                )}
              </Button>
              <button
                onClick={fetchQuestions}
                className="px-4 py-2 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 transition-colors flex items-center gap-2"
                disabled={isGenerating}
              >
                <FiRefreshCw className="h-4 w-4" />
                Refresh
              </button>
              <Button
                onClick={handleVerifyAll}
                disabled={isGenerating || !questions}
                className="bg-green-600 hover:bg-green-700"
              >
                <FiCheckCircle className="h-4 w-4 mr-2" />
                Verify All
              </Button>
            </div>
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

        {/* Question Stats Cards */}
        {questions && questions.metadata ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg hover:border-gray-700 transition-colors">
              <div className="text-xs md:text-sm text-gray-400 mb-1">Total Questions</div>
              <div className="text-2xl md:text-3xl font-bold text-gray-100">
                {questions.metadata.total_questions || 0}
              </div>
            </div>
            {categories.map((cat) => (
              <div
                key={cat}
                className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg cursor-pointer hover:border-gray-700 transition-colors"
                onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault()
                    setSelectedCategory(selectedCategory === cat ? null : cat)
                  }
                }}
              >
                <div className="text-xs md:text-sm text-gray-400 mb-1">{cat}</div>
                <div className="text-2xl md:text-3xl font-bold text-gray-100">
                  {questionCounts[cat] || 0}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mb-6">
            <p className="text-gray-400 text-center">No questions found. Generate questions to get started.</p>
          </div>
        )}

        {/* Questions Display */}
        {questions && questions.questions && Object.keys(questions.questions).length > 0 ? (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg shadow-lg">
            {/* Category Tabs */}
            <div className="border-b border-gray-800/50 bg-gray-800/30">
              <div className="flex overflow-x-auto">
                <button
                  onClick={() => setSelectedCategory(null)}
                  className={`px-6 py-3 text-sm font-medium transition-colors whitespace-nowrap border-b-2 ${
                    !selectedCategory
                      ? "border-blue-500 text-blue-400 bg-gray-900/50"
                      : "border-transparent text-gray-400 hover:text-gray-300"
                  }`}
                >
                  All Questions
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-6 py-3 text-sm font-medium transition-colors whitespace-nowrap border-b-2 ${
                      selectedCategory === cat
                        ? "border-blue-500 text-blue-400 bg-gray-900/50"
                        : "border-transparent text-gray-400 hover:text-gray-300"
                    }`}
                  >
                    {cat} ({questionCounts[cat] || 0})
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 md:p-6">
              {/* Search */}
              {selectedCategory && (
                <div className="mb-4 md:mb-6">
                  <div className="relative">
                    <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Search questions..."
                      className="w-full pl-10 pr-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-600 text-sm md:text-base"
                    />
                  </div>
                </div>
              )}

              {/* Questions Cards Grid */}
              {selectedCategory ? (
                filteredQuestions.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
                    {filteredQuestions.map((q, idx) => (
                      <div
                        key={q.id || idx}
                        className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 md:p-5 hover:border-gray-600 transition-all duration-200 hover:shadow-lg flex flex-col"
                      >
                        {/* Category & Verification Badge */}
                        <div className="flex items-start justify-between mb-3">
                          <span className="px-2 py-1 text-xs font-medium bg-blue-900/50 text-blue-300 rounded shrink-0">
                            {q.category}
                          </span>
                          {q.verified !== undefined && (
                            <span className={`px-2 py-1 text-xs font-medium rounded shrink-0 flex items-center gap-1 ${
                              q.verified
                                ? "bg-green-900/50 text-green-300"
                                : "bg-yellow-900/50 text-yellow-300"
                            }`}>
                              {q.verified ? (
                                <>
                                  <FiShield className="h-3 w-3" />
                                  Verified
                                </>
                              ) : (
                                <>
                                  <FiAlertCircle className="h-3 w-3" />
                                  Unverified
                                </>
                              )}
                            </span>
                          )}
                        </div>

                        {/* Question Type */}
                        {q.type && (
                          <span className="text-xs text-gray-500 mb-2 inline-block">
                            Type: {q.type}
                          </span>
                        )}

                        {/* Question */}
                        <h3 className="text-base md:text-lg font-semibold text-gray-100 mb-4 line-clamp-3 flex-1">
                          {q.question}
                        </h3>

                        {/* Answer */}
                        {q.answer && (
                          <div className="mb-3">
                            <p className="text-xs font-medium text-gray-400 mb-1">Answer</p>
                            <p className="text-sm font-medium text-green-400 break-words">
                              {q.answer}
                            </p>
                          </div>
                        )}

                        {/* Explanation */}
                        {q.explanation && (
                          <div className="mb-3">
                            <p className="text-xs font-medium text-gray-400 mb-1">Explanation</p>
                            <p className="text-xs text-gray-300 break-words">
                              {q.explanation}
                            </p>
                          </div>
                        )}

                        {/* Quality Score */}
                        {q.quality_score !== undefined && (
                          <div className="mt-auto pt-3 border-t border-gray-700">
                            <div className="flex items-center justify-between">
                              <span className="text-xs text-gray-400">Quality Score</span>
                              <span className={`text-sm font-bold ${
                                q.quality_score >= 0.8 ? "text-green-400" :
                                q.quality_score >= 0.6 ? "text-yellow-400" :
                                "text-red-400"
                              }`}>
                                {(q.quality_score * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-400">
                    {searchTerm ? "No questions found matching your search" : "No questions in this category"}
                  </div>
                )
              ) : (
                <div className="text-center py-12 text-gray-400">
                  Select a category to view questions
                </div>
              )}
            </div>
          </div>
        ) : questions ? (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
            <p className="text-gray-400 text-center">No questions available. Click "Generate Questions" to create them.</p>
          </div>
        ) : null}

        {/* Output Log */}
        {output && status === "success" && (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mt-6">
            <h2 className="text-xl font-semibold text-gray-100 mb-4">Generation Results</h2>
            <pre className="bg-gray-950/50 p-4 rounded-lg overflow-x-auto text-sm text-gray-300 font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
              {output}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default QuestionGenerator
