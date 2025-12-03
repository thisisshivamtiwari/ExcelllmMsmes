import { useState, useEffect, useRef } from "react"
import { FiSend, FiLoader, FiAlertCircle, FiCheckCircle, FiMessageSquare, FiChevronDown, FiChevronUp, FiHelpCircle } from "react-icons/fi"
import ChartDisplay from "../components/ChartDisplay"
import SuggestionsPanel from "../components/SuggestionsPanel"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

const AgentChat = () => {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [agentStatus, setAgentStatus] = useState(null)
  const [provider, setProvider] = useState("gemini") // "groq" or "gemini" - Gemini as default
  const [showExamples, setShowExamples] = useState(false) // Collapsed by default
  const messagesEndRef = useRef(null)

  useEffect(() => {
    checkAgentStatus()
  }, [])

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
          if ((parsed.type || parsed.chart_type) && parsed.data) {
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

    if (typeof rawAnswer === "object") {
      if ((rawAnswer.type || rawAnswer.chart_type) && rawAnswer.data) {
        chartConfig = rawAnswer
        textContent = ""
        return { chartConfig, textContent, parseError }
      }
      return { chartConfig: null, textContent: JSON.stringify(rawAnswer, null, 2) }
    }

    if (typeof rawAnswer === "string") {
      const trimmed = rawAnswer.trim()

      if (trimmed.startsWith("{")) {
        if (tryParse(trimmed)) {
          return { chartConfig, textContent, parseError: null }
        }
      }

      const successIndex = trimmed.indexOf('{"success"')
      const chartIndex = trimmed.indexOf('{"chart_type"')
      const startIndex = successIndex !== -1 ? successIndex : chartIndex

      if (startIndex !== -1) {
        const candidate = trimmed.substring(startIndex)
        if (tryParse(candidate)) {
          return { chartConfig, textContent, parseError: null }
        }
      }

      return { chartConfig: null, textContent: rawAnswer, parseError }
    }

    return { chartConfig: null, textContent: String(rawAnswer), parseError }
  }

  const checkAgentStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/agent/status`)
      const data = await response.json()
      setAgentStatus(data)
    } catch (error) {
      console.error("Error checking agent status:", error)
      setAgentStatus({ available: false, error: "Failed to check agent status" })
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
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4 lg:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white mb-2">AI Agent Chat</h1>
          <p className="text-gray-400">Ask questions about your Excel data in natural language</p>
          
          {/* Provider Toggle */}
          <div className="mt-4 flex items-center gap-4">
            <span className="text-sm text-gray-400">Model Provider:</span>
            <div className="flex gap-2 bg-gray-800/50 border border-gray-700/50 rounded-lg p-1">
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
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <FiMessageSquare className="h-16 w-16 mb-4 opacity-50" />
                <p className="text-lg mb-2">Start a conversation</p>
                <p className="text-sm text-center max-w-md">
                  Ask questions about your data, request calculations, analyze trends, or compare entities.
                </p>
                <p className="text-xs text-gray-600 mt-2">
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
                    }`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-4 ${
                        message.role === "user"
                          ? "bg-blue-600/20 border border-blue-500/30"
                          : message.success === false
                          ? "bg-red-900/20 border border-red-700/30"
                          : "bg-gray-800/50 border border-gray-700/50"
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <div className="flex-1">
                          {message.content && (
                            <p className="text-white whitespace-pre-wrap">{message.content}</p>
                          )}
                          
                          {/* Chart Display */}
                          {message.chartConfig && (
                            <ChartDisplay chartConfig={message.chartConfig} />
                          )}
                          
                          {/* Provider Badge */}
                          {message.provider && (
                            <div className="mt-2 inline-block">
                              <span className="text-xs px-2 py-1 rounded bg-gray-700/50 text-gray-300">
                                {message.provider === "groq" ? "🤖 Groq" : "✨ Gemini"}
                                {message.modelName && ` • ${message.modelName}`}
                              </span>
                            </div>
                          )}
                          
                          {/* Intermediate Steps */}
                          {message.intermediateSteps && message.intermediateSteps.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-gray-700/50">
                              <p className="text-xs text-gray-400 mb-2">Reasoning steps:</p>
                              {message.intermediateSteps.map((step, stepIdx) => (
                                <div key={stepIdx} className="text-xs text-gray-500 mb-1">
                                  <span className="text-gray-400">•</span> {step.action || "N/A"}: {step.action_input || "N/A"}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
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

          {/* Input Area */}
          <div className="border-t border-gray-800/50 p-4">
            <form onSubmit={handleSend} className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question about your data..."
                className="flex-1 bg-gray-800/50 border border-gray-700/50 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
                disabled={loading || !agentStatus?.providers?.[provider]?.available}
              />
              <button
                type="submit"
                disabled={loading || !input.trim() || !agentStatus?.providers?.[provider]?.available}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-2"
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
          <div className="bg-gray-800/50 backdrop-blur-xl border border-gray-700/50 rounded-xl overflow-hidden">
            {/* Header */}
            <button
              onClick={() => setShowExamples(!showExamples)}
              className="w-full flex items-center justify-between p-4 hover:bg-gray-800/70 transition-colors"
              disabled={loading}
            >
              <div className="flex items-center gap-2">
                <FiHelpCircle className="text-green-400" />
                <span className="text-white font-medium">Example Queries</span>
                <span className="text-xs text-gray-500 bg-gray-700/50 px-2 py-1 rounded">
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
              <div className="border-t border-gray-700/50 p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {exampleQueries.map((query, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setInput(query)
                        handleSend(null, query)
                      }}
                      className="text-left p-3 rounded-lg bg-gray-700/30 hover:bg-gray-700/60 border border-gray-600/30 hover:border-green-500/50 transition-all text-sm text-gray-300 hover:text-white group"
                      disabled={loading || !agentStatus?.providers?.[provider]?.available}
                    >
                      <div className="flex items-start gap-2">
                        <span className="text-green-400 opacity-50 group-hover:opacity-100 transition-opacity">
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

