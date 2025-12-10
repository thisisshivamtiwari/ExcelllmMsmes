import { useState, useEffect, useRef } from "react"
import { FiSend, FiLoader, FiAlertCircle, FiCheckCircle, FiMessageSquare, FiChevronDown, FiChevronUp, FiHelpCircle } from "react-icons/fi"
import ChartDisplay from "../components/ChartDisplay"
import SuggestionsPanel from "../components/SuggestionsPanel"
import { useAuth } from "@/contexts/AuthContext"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

const AgentChat = () => {
  const { token } = useAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [agentStatus, setAgentStatus] = useState(null)
  const [provider, setProvider] = useState("gemini") // "groq" or "gemini" - Gemini as default
  const [showExamples, setShowExamples] = useState(false) // Collapsed by default
  const messagesEndRef = useRef(null)

  useEffect(() => {
    checkAgentStatus()
  }, [token, provider])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const extractChartConfig = (rawAnswer) => {
    if (!rawAnswer) {
      return { chartConfig: null, textContent: "" }
    }

    let textContent = rawAnswer
    let chartConfig = null
    let parseError = null

    const tryParse = (candidate) => {
      try {
        const parsed = JSON.parse(candidate)
        if (parsed && typeof parsed === "object") {
          // Check for chart data structure
          if ((parsed.type || parsed.chart_type) && parsed.data) {
            chartConfig = parsed
            textContent = ""
            return true
          }
          // Check for success wrapper with chart data
          if (parsed.success && parsed.chart_type && parsed.data) {
            chartConfig = parsed
            textContent = ""
            return true
          }
        }
      } catch (error) {
        parseError = error
      }
      return false
    }

    // If already an object
    if (typeof rawAnswer === "object") {
      if ((rawAnswer.type || rawAnswer.chart_type) && rawAnswer.data) {
        chartConfig = rawAnswer
        textContent = ""
        return { chartConfig, textContent, parseError }
      }
      if (rawAnswer.success && rawAnswer.chart_type && rawAnswer.data) {
        chartConfig = rawAnswer
        textContent = ""
        return { chartConfig, textContent, parseError }
      }
      return { chartConfig: null, textContent: JSON.stringify(rawAnswer, null, 2) }
    }

    // If it's a string, try to parse it
    if (typeof rawAnswer === "string") {
      const trimmed = rawAnswer.trim()

      // Try parsing the entire string first
      if (trimmed.startsWith("{")) {
        if (tryParse(trimmed)) {
          return { chartConfig, textContent, parseError: null }
        }
      }

      // Look for JSON objects in the string
      const patterns = [
        /\{"success"\s*:\s*true.*?"chart_type".*?\}/s,
        /\{"chart_type".*?\}/s,
        /\{"type".*?"data".*?\}/s
      ]

      for (const pattern of patterns) {
        const match = trimmed.match(pattern)
        if (match) {
          // Try to find the complete JSON by counting braces
          let braceCount = 0
          let startIdx = match.index
          let endIdx = startIdx
          
          for (let i = startIdx; i < trimmed.length; i++) {
            if (trimmed[i] === '{') braceCount++
            if (trimmed[i] === '}') braceCount--
            if (braceCount === 0 && trimmed[i] === '}') {
              endIdx = i + 1
              break
            }
          }
          
          const candidate = trimmed.substring(startIdx, endIdx)
          if (tryParse(candidate)) {
            return { chartConfig, textContent, parseError: null }
          }
        }
      }

      return { chartConfig: null, textContent: rawAnswer, parseError }
    }

    return { chartConfig: null, textContent: String(rawAnswer), parseError }
  }

  const checkAgentStatus = async () => {
    if (!token) {
      setAgentStatus({ available: false, message: "Please login to use agent chat" })
      return
    }
    
    try {
      const headers = {
        "Authorization": `Bearer ${token}`
      }
      
      const response = await fetch(`${API_BASE_URL}/agent/status`, { headers })
      if (response.ok) {
        const data = await response.json()
        setAgentStatus(data)
      } else if (response.status === 401) {
        setAgentStatus({ available: false, message: "Please login to use agent chat" })
      } else {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
        setAgentStatus({ available: false, message: errorData.detail || "Failed to check agent status" })
      }
    } catch (error) {
      console.error("Error checking agent status:", error)
      setAgentStatus({ available: false, message: `Error: ${error.message}` })
    }
  }

  const handleSend = async (e, questionText = null, options = {}) => {
    const { isFallback = false, fallbackDepth = 0, providerOverride = null } = options
    if (e) e.preventDefault()

    const activeProvider = providerOverride || provider
    const messageText = questionText || input.trim()
    if (!messageText || (loading && !isFallback)) return

    if (!isFallback) {
      const userMessage = {
        role: "user",
        content: messageText,
        timestamp: new Date().toISOString(),
        provider: activeProvider
      }

      setMessages((prev) => [...prev, userMessage])
      setInput("")
      setLoading(true)
    }

    if (!token) {
      const errorMessage = {
        role: "assistant",
        content: "Please login to use agent chat",
        success: false,
        provider: activeProvider,
        timestamp: new Date().toISOString()
      }
      setMessages((prev) => [...prev, errorMessage])
      setLoading(false)
      return
    }

    try {
      const headers = {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      }
      
      const response = await fetch(`${API_BASE_URL}/agent/query`, {
        method: "POST",
        headers,
        body: JSON.stringify({ 
          question: messageText,
          provider: activeProvider
        })
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("Please login to use agent chat")
        }
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
        throw new Error(errorData.detail || "Failed to process query")
      }

      const data = await response.json()
      const rawAnswer = data.answer || data.error || "No response received"

      const { chartConfig, textContent, parseError } = extractChartConfig(rawAnswer)

      const assistantMessage = {
        role: "assistant",
        content: textContent,
        chartConfig: chartConfig,
        success: data.success,
        intermediateSteps: data.intermediate_steps || [],
        provider: data.provider || activeProvider,
        modelName: data.model_name,
        timestamp: new Date().toISOString()
      }

      setMessages((prev) => [...prev, assistantMessage])

      const jsonErrorMessage = parseError?.message || ""
      const looksLikeTruncation = jsonErrorMessage.includes("Unexpected end") || jsonErrorMessage.includes("Unterminated") || (typeof rawAnswer === "string" && rawAnswer.length > 3500)

      if (!chartConfig && looksLikeTruncation && fallbackDepth < 1) {
        const fallbackQuestion = `${messageText} (limit to the last 60 days)`
        const fallbackNotice = {
          role: "assistant",
          content: "The chart data was too large to render. Fetching a focused view for the last 60 days...",
          success: false,
          provider: activeProvider,
          timestamp: new Date().toISOString()
        }

        setMessages((prev) => [...prev, fallbackNotice])

        await handleSend(null, fallbackQuestion, {
          isFallback: true,
          fallbackDepth: fallbackDepth + 1,
          providerOverride: activeProvider
        })
      }
    } catch (error) {
      const errorMessage = {
        role: "assistant",
        content: `Error: ${error.message}`,
        success: false,
        provider: activeProvider,
        timestamp: new Date().toISOString()
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      if (!isFallback) {
        setLoading(false)
      }
    }
    /* 
    try {
      const response = await fetch(`${API_BASE_URL}/agent/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
          question: messageText,
          provider: activeProvider
        })
      })

      const data = await response.json()
      const rawAnswer = data.answer || data.error || "No response received"

      const { chartConfig, textContent, parseError } = extractChartConfig(rawAnswer)

      const assistantMessage = {
        role: "assistant",
        content: textContent,
        chartConfig: chartConfig,
        success: data.success,
        intermediateSteps: data.intermediate_steps || [],
        provider: data.provider || activeProvider,
        modelName: data.model_name,
        timestamp: new Date().toISOString()
      }

      setMessages((prev) => [...prev, assistantMessage])

      const jsonErrorMessage = parseError?.message || ""
      const looksLikeTruncation = jsonErrorMessage.includes("Unexpected end") || jsonErrorMessage.includes("Unterminated") || (typeof rawAnswer === "string" && rawAnswer.length > 3500)

      if (!chartConfig && looksLikeTruncation && fallbackDepth < 1) {
        const fallbackQuestion = `${messageText} (limit to the last 60 days)`
        const fallbackNotice = {
          role: "assistant",
          content: "The chart data was too large to render. Fetching a focused view for the last 60 days...",
          success: false,
          provider: activeProvider,
          timestamp: new Date().toISOString()
        }

        setMessages((prev) => [...prev, fallbackNotice])

        await handleSend(null, fallbackQuestion, {
          isFallback: true,
          fallbackDepth: fallbackDepth + 1,
          providerOverride: activeProvider
        })
      }
    } catch (error) {
      const errorMessage = {
        role: "assistant",
        content: `Error: ${error.message}`,
        success: false,
        provider: activeProvider,
        timestamp: new Date().toISOString()
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      if (!isFallback) {
        setLoading(false)
      }
    }
    */
  }

  const handleSuggestionSelect = (question) => {
    setInput(question)
    handleSend(null, question)
  }

  const exampleQueries = [
    "What is the total production quantity?",
    "Which product has the most defects?",
    "Show me production trends over the last month",
    "Compare production efficiency across different lines",
    "Calculate OEE for all machines"
  ]

  return (
    <div className="p-4 min-h-screen text-gray-100 bg-gray-950 lg:p-8">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-6">
          <h1 className="mb-2 text-3xl font-bold text-white">AI Agent Chat</h1>
          <p className="text-gray-400">Ask questions about your Excel data in natural language</p>
          
          {/* Provider Toggle */}
          <div className="flex gap-4 items-center mt-4">
            <span className="text-sm text-gray-400">Model Provider:</span>
            <div className="flex gap-2 p-1 rounded-lg border bg-gray-800/50 border-gray-700/50">
              <button
                onClick={() => setProvider("groq")}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  provider === "groq"
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-white"
                }`}
                disabled={loading}
              >
                Groq
              </button>
              <button
                onClick={() => setProvider("gemini")}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  provider === "gemini"
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-white"
                }`}
                disabled={loading}
              >
                Gemini
              </button>
            </div>
            {agentStatus?.providers?.[provider] && (
              <span className="text-xs text-gray-500">
                ({agentStatus.providers[provider].model_name})
              </span>
            )}
          </div>
          
          {/* Agent Status */}
          {agentStatus && (
            <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
              agentStatus.providers?.[provider]?.available
                ? "bg-green-900/30 border border-green-700/50" 
                : "bg-red-900/30 border border-red-700/50"
            }`}>
              {agentStatus.providers?.[provider]?.available ? (
                <>
                  <FiCheckCircle className="text-green-400" />
                  <span className="text-sm text-green-300">
                    {provider === "groq" ? "Groq" : "Gemini"} agent is ready
                    {agentStatus.providers[provider].model_name && ` (${agentStatus.providers[provider].model_name})`}
                  </span>
                </>
              ) : (
                <>
                  <FiAlertCircle className="text-red-400" />
                  <span className="text-sm text-red-300">
                    {provider === "groq" ? "Groq" : "Gemini"} agent unavailable: {
                      agentStatus.providers?.[provider]?.api_key_set 
                        ? "Not initialized - check logs" 
                        : "API key not set"
                    }
                  </span>
                </>
              )}
            </div>
          )}
        </div>

        {/* Chat Container */}
        <div className="bg-gray-900/50 backdrop-blur-xl border border-gray-800/50 rounded-xl shadow-2xl flex flex-col h-[calc(100vh-300px)]">
          {/* Messages Area */}
          <div className="overflow-y-auto flex-1 p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col justify-center items-center h-full text-gray-500">
                <FiMessageSquare className="mb-4 w-16 h-16 opacity-50" />
                <p className="mb-2 text-lg">Start a conversation</p>
                <p className="max-w-md text-sm text-center">
                  Ask questions about your data, request calculations, analyze trends, or compare entities.
                </p>
                <p className="mt-2 text-xs text-gray-600">
                  💡 Tip: Check the collapsible sections below for examples and graph suggestions
                </p>
              </div>
            ) : (
              <>
                {messages.map((message, idx) => (
                  <div
                    key={idx}
                    className={`flex gap-4 ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    } animate-fade-in`}
                  >
                    <div
                      className={`${
                        message.chartConfig ? "max-w-[90%]" : "max-w-[80%]"
                      } rounded-xl p-5 shadow-lg ${
                        message.role === "user"
                          ? "bg-gradient-to-r from-blue-600 to-blue-500 text-white"
                          : message.success === false
                          ? "bg-red-900/30 border border-red-700/50"
                          : "bg-gradient-to-br from-gray-800 to-gray-850 border border-gray-700/50"
                      }`}
                    >
                      <div className="flex gap-3 items-start">
                        <div className="flex-1">
                          {message.content && !message.chartConfig && (
                            <p className="leading-relaxed text-white whitespace-pre-wrap">{message.content}</p>
                          )}
                          
                          {/* Chart Display - Bigger and More Beautiful */}
                          {message.chartConfig && (
                            <div className="space-y-3">
                              <ChartDisplay chartConfig={message.chartConfig} />
                            </div>
                          )}
                          
                          {/* Provider Badge */}
                          {message.provider && (
                            <div className="flex gap-2 items-center mt-3">
                              <span className={`text-xs px-3 py-1.5 rounded-full font-medium ${
                                message.provider === "groq" 
                                  ? "bg-blue-500/20 text-blue-300 border border-blue-500/30" 
                                  : "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                              }`}>
                                {message.provider === "groq" ? "🤖 Groq" : "✨ Gemini"}
                                {message.modelName && ` • ${message.modelName}`}
                              </span>
                            </div>
                          )}
                          
                          {/* Intermediate Steps */}
                          {message.intermediateSteps && message.intermediateSteps.length > 0 && (
                            <details className="pt-3 mt-3 border-t border-gray-700/50">
                              <summary className="mb-2 text-xs text-gray-400 cursor-pointer hover:text-gray-300">
                                🔍 View reasoning steps ({message.intermediateSteps.length})
                              </summary>
                              <div className="mt-2 space-y-1">
                                {message.intermediateSteps.map((step, stepIdx) => (
                                  <div key={stepIdx} className="pl-3 text-xs text-gray-500 border-l-2 border-gray-700">
                                    <span className="text-gray-400">Step {stepIdx + 1}:</span> {step.action || "N/A"}: {step.action_input || "N/A"}
                                  </div>
                                ))}
                              </div>
                            </details>
                          )}
                        </div>
                      </div>
                      <p className="flex gap-2 items-center mt-3 text-xs text-gray-500">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-400"></span>
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex gap-4 justify-start">
                    <div className="p-4 rounded-lg border bg-gray-800/50 border-gray-700/50">
                      <div className="flex gap-2 items-center">
                        <FiLoader className="text-blue-400 animate-spin" />
                        <span className="text-gray-400">Thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-gray-800/50">
            <form onSubmit={handleSend} className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question about your data..."
                className="flex-1 px-4 py-3 placeholder-gray-500 text-white rounded-lg border bg-gray-800/50 border-gray-700/50 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
                disabled={loading || !agentStatus?.providers?.[provider]?.available}
              />
              <button
                type="submit"
                disabled={loading || !input.trim() || !agentStatus?.available || !agentStatus?.providers?.[provider]?.available}
                className="flex gap-2 items-center px-6 py-3 text-white bg-blue-600 rounded-lg transition-colors hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <FiLoader className="animate-spin" />
                    <span>Processing</span>
                  </>
                ) : (
                  <>
                    <FiSend />
                    <span>Send</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Collapsible Sections at Bottom */}
        <div className="mt-4 space-y-3">
          {/* Graph Suggestions Panel */}
          <SuggestionsPanel 
            onSelectQuestion={handleSuggestionSelect}
            disabled={loading || !agentStatus?.providers?.[provider]?.available}
          />

          {/* Example Queries Panel */}
          <div className="overflow-hidden rounded-xl border backdrop-blur-xl bg-gray-800/50 border-gray-700/50">
            {/* Header */}
            <button
              onClick={() => setShowExamples(!showExamples)}
              className="flex justify-between items-center p-4 w-full transition-colors hover:bg-gray-800/70"
              disabled={loading}
            >
              <div className="flex gap-2 items-center">
                <FiHelpCircle className="text-green-400" />
                <span className="font-medium text-white">Example Queries</span>
                <span className="px-2 py-1 text-xs text-gray-500 rounded bg-gray-700/50">
                  {exampleQueries.length} examples
                </span>
              </div>
              {showExamples ? (
                <FiChevronUp className="text-gray-400" />
              ) : (
                <FiChevronDown className="text-gray-400" />
              )}
            </button>

            {/* Expanded Content */}
            {showExamples && (
              <div className="p-4 border-t border-gray-700/50">
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  {exampleQueries.map((query, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setInput(query)
                        handleSend(null, query)
                      }}
                      className="p-3 text-sm text-left text-gray-300 rounded-lg border transition-all bg-gray-700/30 hover:bg-gray-700/60 border-gray-600/30 hover:border-green-500/50 hover:text-white group"
                      disabled={loading || !agentStatus?.providers?.[provider]?.available}
                    >
                      <div className="flex gap-2 items-start">
                        <span className="text-green-400 opacity-50 transition-opacity group-hover:opacity-100">
                          •
                        </span>
                        <span className="flex-1">{query}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AgentChat

