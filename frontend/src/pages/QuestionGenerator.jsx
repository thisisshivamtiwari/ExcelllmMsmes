import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { FiPlay, FiRefreshCw, FiFileText, FiCheckCircle, FiAlertCircle, FiLoader, FiSearch } from "react-icons/fi"

const QuestionGenerator = () => {
  const [isGenerating, setIsGenerating] = useState(false)
  const [status, setStatus] = useState(null)
  const [message, setMessage] = useState("")
  const [output, setOutput] = useState("")
  const [questions, setQuestions] = useState(null)
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [searchTerm, setSearchTerm] = useState("")

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  useEffect(() => {
    fetchQuestions()
  }, [])

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

  const fetchQuestions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/question-generator/questions`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      if (data && Object.keys(data).length > 0) {
        setQuestions(data)
      }
    } catch (error) {
      console.error("Error fetching questions:", error)
    }
  }

  const handleGenerate = async () => {
    setIsGenerating(true)
    setStatus(null)
    setMessage("")
    setOutput("")

    try {
      const response = await fetch(`${API_BASE_URL}/question-generator/generate`, {
        method: "POST",
      })

      const data = await response.json()

      if (data.status === "success") {
        setStatus("success")
        setMessage(data.message)
        setOutput(data.output || "")
        if (data.questions) {
          setQuestions(data.questions)
        } else {
          // Refresh questions after generation
          setTimeout(() => fetchQuestions(), 1000)
        }
      } else {
        setStatus("error")
        setMessage(data.message || "Question generation failed")
        setOutput(data.output || "")
      }
    } catch (error) {
      setStatus("error")
      setMessage(`Error: ${error.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const categories = ["Easy", "Medium", "Complex"]
  const questionCounts = questions?.metadata?.questions_by_category || {}

  const filteredQuestions = selectedCategory && questions?.questions?.[selectedCategory]
    ? questions.questions[selectedCategory].filter((q) =>
        searchTerm
          ? q.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
            q.sql_formula?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            q.calculation_steps?.some((step) => step.toLowerCase().includes(searchTerm.toLowerCase()))
          : true
      )
    : []

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-100 mb-2">Question Generator</h1>
          <p className="text-gray-400">
            Generate categorized questions (Easy, Medium, Complex) with SQL formulas and answers from CSV data
          </p>
        </div>

        {/* Generate Button Card - Responsive */}
        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg mb-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex-1">
              <h2 className="text-lg md:text-xl font-semibold text-gray-100 mb-2">Generate Questions</h2>
              <p className="text-xs md:text-sm text-gray-400">
                Analyzes all CSV files and generates questions with SQL formulas and correct answers
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
              <button
                onClick={fetchQuestions}
                className="px-4 py-2 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 transition-colors flex items-center justify-center gap-2 text-sm"
                tabIndex={0}
              >
                <FiRefreshCw className="h-4 w-4" />
                <span>Refresh</span>
              </button>
              <Button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="w-full sm:w-auto shrink-0"
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

        {/* Question Stats Cards - Responsive */}
        {questions ? (
          questions.metadata ? (
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
              <p className="text-gray-400 text-center">No questions metadata found</p>
            </div>
          )
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
              {/* Search - Responsive */}
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
                        {/* Category Badge */}
                        <div className="flex items-start justify-between mb-3">
                          <span className="px-2 py-1 text-xs font-medium bg-blue-900/50 text-blue-300 rounded shrink-0">
                            {q.category}
                          </span>
                        </div>

                        {/* Question */}
                        <h3 className="text-base md:text-lg font-semibold text-gray-100 mb-4 line-clamp-3 flex-1">
                          {q.question}
                        </h3>

                        {/* SQL Formula */}
                        <div className="mb-3">
                          <p className="text-xs font-medium text-gray-400 mb-1.5">SQL Formula</p>
                          <code className="block p-2 bg-gray-950/50 rounded text-xs text-gray-300 font-mono break-words overflow-x-auto">
                            {q.sql_formula || "N/A"}
                          </code>
                        </div>

                        {/* Excel Formula */}
                        <div className="mb-3">
                          <p className="text-xs font-medium text-gray-400 mb-1.5">Excel Formula</p>
                          <code className="block p-2 bg-gray-950/50 rounded text-xs text-gray-300 font-mono break-words overflow-x-auto">
                            {q.excel_formula || "N/A"}
                          </code>
                        </div>

                        {/* Methodology / Calculation Steps */}
                        {q.calculation_steps && q.calculation_steps.length > 0 && (
                          <div className="mb-3">
                            <p className="text-xs font-medium text-gray-400 mb-1.5">Methodology</p>
                            <div className="bg-gray-950/50 rounded p-2 space-y-1">
                              {q.calculation_steps.map((step, stepIdx) => (
                                <div key={stepIdx} className="flex items-start gap-2 text-xs text-gray-300">
                                  <span className="text-blue-400 font-bold shrink-0">{stepIdx + 1}.</span>
                                  <span className="flex-1">{step}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Correct Answer */}
                        {q.correct_answer && (
                          <div className="mt-auto pt-3 border-t border-gray-700">
                            <p className="text-xs font-medium text-gray-400 mb-1">Correct Answer</p>
                            <p className="text-base md:text-lg font-bold text-green-400 break-words">
                              {q.correct_answer}
                            </p>
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

export default QuestionGenerator

