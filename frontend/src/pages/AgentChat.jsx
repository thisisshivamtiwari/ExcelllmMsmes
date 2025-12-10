import { useState, useEffect, useRef } from "react"
import { FiSend, FiLoader, FiAlertCircle, FiCheckCircle, FiMessageSquare, FiRefreshCw, FiChevronDown, FiChevronUp, FiX } from "react-icons/fi"
import ChartDisplay from "../components/ChartDisplay"
import { useAuth } from "@/contexts/AuthContext"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

const AgentChat = () => {
  const { token } = useAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [agentStatus, setAgentStatus] = useState(null)
  const [provider, setProvider] = useState("gemini") // "groq" or "gemini" - Gemini as default
  const [conversationId, setConversationId] = useState(null) // Track conversation ID for multi-turn
  const [pendingDateRange, setPendingDateRange] = useState(null) // Track pending date range request
  const [dateRangeInput, setDateRangeInput] = useState("") // User's date range input
  const [suggestions, setSuggestions] = useState({ text_queries: [], graph_queries: [] }) // Question suggestions
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [suggestionsExpanded, setSuggestionsExpanded] = useState(true) // Floating card expanded state
  const inputRef = useRef(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    checkAgentStatus()
    fetchSuggestions()
  }, [token, provider])

  const fetchSuggestions = async (regenerate = false) => {
    if (!token) return
    setLoadingSuggestions(true)
    try {
      const url = `${API_BASE_URL}/agent/suggestions${regenerate ? '?regenerate=true' : ''}`
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
      const data = await response.json()
      if (data.success) {
        setSuggestions({
          text_queries: data.text_queries || [],
          graph_queries: data.graph_queries || []
        })
      }
    } catch (error) {
      console.error("Error fetching suggestions:", error)
    } finally {
      setLoadingSuggestions(false)
    }
  }

  const handleRegenerateSuggestions = async () => {
    await fetchSuggestions(true)
  }

  const handleSuggestionClick = (query) => {
    setInput(query)
    // Focus the input box so user can see and edit the query
    setTimeout(() => {
      inputRef.current?.focus()
    }, 50)
  }

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

  // Parse date range input (supports "last 30 days", "last month", "2025-11-01 to 2025-12-31", etc.)
  const parseDateRange = (input) => {
    const trimmed = input.trim().toLowerCase()
    const today = new Date()
    let start = null
    let end = null

    // Handle "last N days"
    const lastDaysMatch = trimmed.match(/last\s+(\d+)\s+days?/)
    if (lastDaysMatch) {
      const days = parseInt(lastDaysMatch[1])
      end = new Date(today)
      start = new Date(today)
      start.setDate(start.getDate() - days)
      return { start: start.toISOString().split('T')[0], end: end.toISOString().split('T')[0] }
    }

    // Handle "last month"
    if (trimmed.includes("last month")) {
      end = new Date(today.getFullYear(), today.getMonth(), 0) // Last day of previous month
      start = new Date(today.getFullYear(), today.getMonth() - 1, 1) // First day of previous month
      return { start: start.toISOString().split('T')[0], end: end.toISOString().split('T')[0] }
    }

    // Handle "this month"
    if (trimmed.includes("this month")) {
      start = new Date(today.getFullYear(), today.getMonth(), 1)
      end = new Date(today)
      return { start: start.toISOString().split('T')[0], end: end.toISOString().split('T')[0] }
    }

    // Handle date range format "YYYY-MM-DD to YYYY-MM-DD" or "YYYY-MM-DD - YYYY-MM-DD"
    const dateRangeMatch = trimmed.match(/(\d{4}-\d{2}-\d{2})\s*(?:to|-)\s*(\d{4}-\d{2}-\d{2})/)
    if (dateRangeMatch) {
      return { start: dateRangeMatch[1], end: dateRangeMatch[2] }
    }

    // Handle single date (use as end date, start 30 days before)
    const singleDateMatch = trimmed.match(/(\d{4}-\d{2}-\d{2})/)
    if (singleDateMatch) {
      end = new Date(singleDateMatch[1])
      start = new Date(end)
      start.setDate(start.getDate() - 30)
      return { start: start.toISOString().split('T')[0], end: end.toISOString().split('T')[0] }
    }

    // Default: last 30 days
    end = new Date(today)
    start = new Date(today)
    start.setDate(start.getDate() - 30)
    return { start: start.toISOString().split('T')[0], end: end.toISOString().split('T')[0] }
  }

  const handleSend = async (e, questionText = null, options = {}) => {
    const { isFallback = false, fallbackDepth = 0, providerOverride = null, isDateRangeResponse = false } = options
    if (e) e.preventDefault()

    const activeProvider = providerOverride || provider
    let messageText = questionText || input.trim()
    
    // If this is a date range response, parse it
    let dateRange = null
    if (isDateRangeResponse && dateRangeInput.trim()) {
      dateRange = parseDateRange(dateRangeInput)
      messageText = dateRangeInput.trim() // Use the date range input as the message
      setDateRangeInput("")
      setPendingDateRange(null)
    }
    
    if (!messageText || (loading && !isFallback)) return

    if (!isFallback) {
      // If this is a new question (not a date range follow-up), reset conversation context
      if (!isDateRangeResponse && !conversationId) {
        // Starting a new conversation - clear any pending date range
        setPendingDateRange(null)
        setDateRangeInput("")
      }
      
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
      
      const requestBody = { 
        question: messageText,
        provider: activeProvider
      }
      
      // Add conversation_id if available
      if (conversationId) {
        requestBody.conversation_id = conversationId
      }
      
      // Add date_range if this is a date range response
      if (dateRange) {
        requestBody.date_range = dateRange
      }
      
      const response = await fetch(`${API_BASE_URL}/agent/query`, {
        method: "POST",
        headers,
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("Please login to use agent chat")
        }
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
        throw new Error(errorData.detail || "Failed to process query")
      }

      const data = await response.json()
      
      // Store conversation_id if provided
      if (data.conversation_id) {
        setConversationId(data.conversation_id)
      }
      
      // Check if date range is required
      if (data.requires_date_range && data.date_range_info) {
        setPendingDateRange(data.date_range_info)
      }
      
      // Handle new agent response format (answer_short/answer_detailed) or old format (answer)
      const rawAnswer = data.answer_short || data.answer_detailed || data.answer || data.error || "No response received"
      const chartConfigFromResponse = data.chart_config || null

      const { chartConfig, textContent, parseError } = extractChartConfig(rawAnswer)

      const assistantMessage = {
        role: "assistant",
        content: textContent,
        chartConfig: chartConfig || chartConfigFromResponse,
        success: data.success !== false,
        intermediateSteps: data.intermediate_steps || [],
        provider: data.provider || activeProvider,
        modelName: data.model_name,
        timestamp: data.timestamp || new Date().toISOString(),
        requiresDateRange: data.requires_date_range || false,
        dateRangeInfo: data.date_range_info || null
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


  return (
    <div className="h-full bg-gray-950 text-gray-100 flex flex-col overflow-hidden">
      {/* Compact Header - Fixed at top */}
      <div className="flex-shrink-0 border-b border-gray-800/50 bg-gray-900/80 backdrop-blur-xl px-4 py-2 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
          {/* Provider Toggle */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Model:</span>
            <div className="flex gap-1 bg-gray-800/50 border border-gray-700/50 rounded-lg p-0.5">
              <button
                onClick={() => setProvider("groq")}
                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
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
                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
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
            <div className={`px-2 py-1 rounded flex items-center gap-1.5 ${
              agentStatus.providers?.[provider]?.available
                ? "bg-green-900/30 border border-green-700/50" 
                : "bg-red-900/30 border border-red-700/50"
            }`}>
              {agentStatus.providers?.[provider]?.available ? (
                <>
                  <FiCheckCircle className="text-green-400 text-xs" />
                  <span className="text-xs text-green-300">
                    {provider === "groq" ? "Groq" : "Gemini"} ready
                  </span>
                </>
              ) : (
                <>
                  <FiAlertCircle className="text-red-400 text-xs" />
                  <span className="text-xs text-red-300">
                    {provider === "groq" ? "Groq" : "Gemini"} unavailable
                  </span>
                </>
              )}
            </div>
          )}
          
          {/* New Chat Button */}
          {messages.length > 0 && (
            <button
              onClick={() => {
                setMessages([])
                setConversationId(null)
                setPendingDateRange(null)
                setDateRangeInput("")
                setInput("")
              }}
              className="px-3 py-1 bg-gray-800 hover:bg-gray-700 text-white rounded transition-colors flex items-center gap-1.5 text-xs"
              title="Start new conversation"
            >
              <FiRefreshCw className="text-sm" />
              <span>New Chat</span>
            </button>
          )}
        </div>
      </div>

      {/* Messages Area - Scrollable */}
      <div className="flex-1 overflow-y-auto min-h-0 relative">
        <div className="max-w-7xl mx-auto w-full p-4 lg:p-6 space-y-4 pb-24">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 py-20">
                <FiMessageSquare className="h-20 w-20 mb-6 opacity-50" />
                <p className="text-xl lg:text-2xl mb-3 font-medium">Start a conversation</p>
                <p className="text-sm lg:text-base text-center max-w-lg text-gray-400 mb-8">
                  Ask questions about your data, request calculations, analyze trends, or compare entities.
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
                        message.chartConfig ? "max-w-[95%] lg:max-w-[90%]" : "max-w-[90%] lg:max-w-[85%]"
                      } rounded-xl p-5 lg:p-6 shadow-lg ${
                        message.role === "user"
                          ? "bg-gradient-to-r from-blue-600 to-blue-500 text-white"
                          : message.success === false
                          ? "bg-red-900/30 border border-red-700/50"
                          : "bg-gradient-to-br from-gray-800 to-gray-850 border border-gray-700/50"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex-1">
                          {message.content && !message.chartConfig && (
                            <p className="text-white whitespace-pre-wrap leading-relaxed">{message.content}</p>
                          )}
                          
                          {/* Date Range Request UI */}
                          {message.requiresDateRange && message.dateRangeInfo && (
                            <div className="mt-4 p-4 bg-blue-900/30 border border-blue-700/50 rounded-lg">
                              <p className="text-sm text-blue-200 mb-3">
                                📅 Please specify a date range to analyze:
                              </p>
                              <div className="flex flex-col gap-2">
                                <input
                                  type="text"
                                  value={dateRangeInput}
                                  onChange={(e) => setDateRangeInput(e.target.value)}
                                  placeholder='e.g., "last 30 days", "last month", or "2025-11-01 to 2025-12-31"'
                                  className="bg-gray-800/50 border border-gray-700/50 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                  onKeyPress={(e) => {
                                    if (e.key === 'Enter' && dateRangeInput.trim()) {
                                      handleSend(null, null, { isDateRangeResponse: true })
                                    }
                                  }}
                                />
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => {
                                      setDateRangeInput("last 30 days")
                                      handleSend(null, null, { isDateRangeResponse: true })
                                    }}
                                    className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                                  >
                                    Last 30 Days
                                  </button>
                                  <button
                                    onClick={() => {
                                      setDateRangeInput("last month")
                                      handleSend(null, null, { isDateRangeResponse: true })
                                    }}
                                    className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                                  >
                                    Last Month
                                  </button>
                                  <button
                                    onClick={() => {
                                      if (message.dateRangeInfo?.min_date && message.dateRangeInfo?.max_date) {
                                        setDateRangeInput(`${message.dateRangeInfo.min_date} to ${message.dateRangeInfo.max_date}`)
                                        handleSend(null, null, { isDateRangeResponse: true })
                                      }
                                    }}
                                    className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
                                  >
                                    All Data
                                  </button>
                                  {dateRangeInput.trim() && (
                                    <button
                                      onClick={() => handleSend(null, null, { isDateRangeResponse: true })}
                                      className="px-3 py-1.5 text-xs bg-green-600 hover:bg-green-700 text-white rounded transition-colors ml-auto"
                                    >
                                      Submit
                                    </button>
                                  )}
                                </div>
                                {message.dateRangeInfo && (
                                  <p className="text-xs text-gray-400 mt-2">
                                    Available range: {message.dateRangeInfo.min_date} to {message.dateRangeInfo.max_date} ({message.dateRangeInfo.span_days} days, {message.dateRangeInfo.row_count} rows)
                                  </p>
                                )}
                              </div>
                            </div>
                          )}
                          
                          {/* Chart Display - Bigger and More Beautiful */}
                          {message.chartConfig && (
                            <div className="space-y-3">
                              <ChartDisplay chartConfig={message.chartConfig} />
                            </div>
                          )}
                          
                          {/* Provider Badge */}
                          {message.provider && (
                            <div className="mt-3 flex items-center gap-2">
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
                            <details className="mt-3 pt-3 border-t border-gray-700/50">
                              <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-300 mb-2">
                                🔍 View reasoning steps ({message.intermediateSteps.length})
                              </summary>
                              <div className="mt-2 space-y-1">
                                {message.intermediateSteps.map((step, stepIdx) => (
                                  <div key={stepIdx} className="text-xs text-gray-500 pl-3 border-l-2 border-gray-700">
                                    <span className="text-gray-400">Step {stepIdx + 1}:</span> {step.action || "N/A"}: {step.action_input || "N/A"}
                                  </div>
                                ))}
                              </div>
                            </details>
                          )}
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-3 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-400"></span>
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex gap-4 justify-start">
                    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                      <div className="flex items-center gap-2">
                        <FiLoader className="animate-spin text-blue-400" />
                        <span className="text-gray-400">Thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
        </div>
      </div>

      {/* Input Area - Fixed at bottom with glass card */}
      {/* Floating Suggestions Card - Above Input */}
      {(suggestions.text_queries.length > 0 || suggestions.graph_queries.length > 0) && (
        <div className="flex-shrink-0 pb-2 px-4 pt-2 relative z-20">
          <div className="max-w-7xl mx-auto w-full">
            <div className="bg-gray-800/60 border border-gray-700/50 rounded-lg shadow-xl mb-2">
              <div className="flex items-center justify-between p-3 border-b border-gray-700/50">
                <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                  <FiMessageSquare className="text-blue-400" />
                  Suggested Queries
                </h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleRegenerateSuggestions}
                    disabled={loadingSuggestions}
                    className="text-xs px-2 py-1 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 rounded text-blue-300 hover:text-blue-200 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Generate more questions using Gemini AI"
                  >
                    {loadingSuggestions ? (
                      <>
                        <FiLoader className="animate-spin text-xs" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <FiRefreshCw className="text-xs" />
                        Generate More
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setSuggestionsExpanded(!suggestionsExpanded)}
                    className="text-gray-400 hover:text-gray-200 transition-colors p-1"
                    title={suggestionsExpanded ? "Collapse" : "Expand"}
                  >
                    {suggestionsExpanded ? <FiChevronUp /> : <FiChevronDown />}
                  </button>
                </div>
              </div>
              
              {suggestionsExpanded && (
                <div className="p-4 space-y-4 max-h-64 overflow-y-auto">
                  {/* Text Query Suggestions */}
                  {suggestions.text_queries.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">Text Queries</h4>
                      <div className="flex flex-wrap gap-2">
                        {suggestions.text_queries.map((query, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleSuggestionClick(query)}
                            className="px-3 py-1.5 bg-gray-700/50 hover:bg-gray-600/50 border border-gray-600/50 rounded-lg text-sm text-gray-200 hover:text-white transition-colors"
                            disabled={loading}
                          >
                            {query}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Graph Query Suggestions */}
                  {suggestions.graph_queries.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">Chart Queries</h4>
                      <div className="flex flex-wrap gap-2">
                        {suggestions.graph_queries.map((query, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleSuggestionClick(query)}
                            className="px-3 py-1.5 bg-blue-900/40 hover:bg-blue-800/50 border border-blue-700/50 rounded-lg text-sm text-blue-200 hover:text-blue-100 transition-colors"
                            disabled={loading}
                          >
                            📊 {query}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="flex-shrink-0 pb-4 px-4 pt-2 relative z-20">
        <div className="max-w-7xl mx-auto w-full">
          <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-700/40 rounded-xl shadow-2xl p-3">
            {pendingDateRange ? (
              <div className="bg-blue-900/20 border border-blue-700/30 rounded-lg p-4">
                <p className="text-sm text-blue-200 mb-3 font-medium">
                  📅 Specify a date range to continue:
                </p>
                <div className="flex flex-col lg:flex-row gap-2">
                  <input
                    type="text"
                    value={dateRangeInput}
                    onChange={(e) => setDateRangeInput(e.target.value)}
                    placeholder='e.g., "last 30 days", "last month", or "2025-11-01 to 2025-12-31"'
                    className="flex-1 bg-gray-800/40 border border-gray-700/40 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && dateRangeInput.trim()) {
                        handleSend(null, null, { isDateRangeResponse: true })
                      }
                    }}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setDateRangeInput("last 30 days")
                        handleSend(null, null, { isDateRangeResponse: true })
                      }}
                      className="px-3 py-2 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
                    >
                      Last 30 Days
                    </button>
                    <button
                      onClick={() => {
                        setDateRangeInput("last month")
                        handleSend(null, null, { isDateRangeResponse: true })
                      }}
                      className="px-3 py-2 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
                    >
                      Last Month
                    </button>
                    {dateRangeInput.trim() && (
                      <button
                        onClick={() => handleSend(null, null, { isDateRangeResponse: true })}
                        className="px-3 py-2 text-xs bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors font-medium"
                      >
                        Submit
                      </button>
                    )}
                  </div>
                </div>
                {pendingDateRange && (
                  <p className="text-xs text-gray-400 mt-2">
                    Available: {pendingDateRange.min_date} to {pendingDateRange.max_date} ({pendingDateRange.span_days} days, {pendingDateRange.row_count} rows)
                  </p>
                )}
              </div>
            ) : (
              <form onSubmit={handleSend} className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question about your data..."
                  className="flex-1 bg-gray-800/40 border border-gray-700/40 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
                  disabled={loading || !agentStatus?.providers?.[provider]?.available}
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim() || !agentStatus?.available || !agentStatus?.providers?.[provider]?.available}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-1.5 text-sm font-medium"
                >
                  {loading ? (
                    <>
                      <FiLoader className="animate-spin text-xs" />
                      <span>Processing</span>
                    </>
                  ) : (
                    <>
                      <FiSend className="text-xs" />
                      <span>Send</span>
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AgentChat

