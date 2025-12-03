import { useState, useEffect, useRef } from "react"
import { FiSend, FiLoader, FiAlertCircle, FiCheckCircle, FiMessageSquare } from "react-icons/fi"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

const AgentChat = () => {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [agentStatus, setAgentStatus] = useState(null)
  const [provider, setProvider] = useState("groq") // "groq" or "gemini"
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

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = {
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
      provider: provider
    }

    setMessages((prev) => [...prev, userMessage])
    const currentInput = input.trim()
    setInput("")
    setLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/agent/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
          question: currentInput,
          provider: provider
        })
      })

      const data = await response.json()

      const assistantMessage = {
        role: "assistant",
        content: data.answer || data.error || "No response received",
        success: data.success,
        intermediateSteps: data.intermediate_steps || [],
        provider: data.provider || provider,
        modelName: data.model_name,
        timestamp: new Date().toISOString()
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = {
        role: "assistant",
        content: `Error: ${error.message}`,
        success: false,
        provider: provider,
        timestamp: new Date().toISOString()
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
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
        <div className="bg-gray-900/50 backdrop-blur-xl border border-gray-800/50 rounded-xl shadow-2xl flex flex-col h-[calc(100vh-250px)]">
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <FiMessageSquare className="h-16 w-16 mb-4 opacity-50" />
                <p className="text-lg mb-2">Start a conversation</p>
                <p className="text-sm text-center max-w-md">
                  Ask questions about your data, request calculations, analyze trends, or compare entities.
                </p>
                
                {/* Example Queries */}
                <div className="mt-6 w-full max-w-2xl">
                  <p className="text-sm text-gray-500 mb-3">Example queries:</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {exampleQueries.map((query, idx) => (
                      <button
                        key={idx}
                        onClick={() => setInput(query)}
                        className="text-left p-3 rounded-lg bg-gray-800/50 hover:bg-gray-800 border border-gray-700/50 hover:border-gray-600 transition-colors text-sm text-gray-300 hover:text-white"
                      >
                        {query}
                      </button>
                    ))}
                  </div>
                </div>
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
                          <p className="text-white whitespace-pre-wrap">{message.content}</p>
                          
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
      </div>
    </div>
  )
}

export default AgentChat

