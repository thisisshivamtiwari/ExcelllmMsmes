import { useState, useEffect } from "react"
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider, useAuth } from "@/contexts/AuthContext"
import Header from "@/components/Header"
import Sidebar from "@/components/Sidebar"
import ProtectedRoute from "@/components/ProtectedRoute"
import Login from "@/pages/Login"
import Signup from "@/pages/Signup"
import Dashboard from "@/pages/Dashboard"
import DataGenerator from "@/pages/DataGenerator"
import Visualization from "@/pages/Visualization"
import VisualizationDynamic from "@/pages/VisualizationDynamic"
import QuestionGenerator from "@/pages/QuestionGenerator"
import Benchmarking from "@/pages/Benchmarking"
import PromptEngineering from "@/pages/PromptEngineering"
import ComparisonAnalysis from "@/pages/ComparisonAnalysis"
import FileUpload from "@/pages/FileUpload"
import SemanticSearch from "@/pages/SemanticSearch"
import AgentChat from "@/pages/AgentChat"
import SystemReport from "@/pages/SystemReport"

// Public route wrapper (redirects to dashboard if already logged in)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-950">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return children
}

// Main app content (requires auth context)
const AppContent = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)

  // Handle window resize - keep sidebar open on desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setIsSidebarOpen(true)
      } else {
        setIsSidebarOpen(false)
      }
    }

    // Set initial state
    handleResize()

    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  const handleSidebarClose = () => {
    setIsSidebarOpen(false)
  }

  const handleMenuClick = () => {
    setIsSidebarOpen(!isSidebarOpen)
  }

  const handleToggleCollapse = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed)
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />
      <Route
        path="/signup"
        element={
          <PublicRoute>
            <Signup />
          </PublicRoute>
        }
      />

      {/* Protected Routes */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <div className="flex h-screen bg-gray-950 overflow-hidden">
              <Sidebar
                isOpen={isSidebarOpen}
                onClose={handleSidebarClose}
                isCollapsed={isSidebarCollapsed}
                onToggleCollapse={handleToggleCollapse}
              />
              <div
                className={`flex flex-col flex-1 transition-all duration-300 overflow-hidden ${
                  isSidebarCollapsed ? "lg:ml-20" : "lg:ml-64"
                }`}
              >
                <Header onMenuClick={handleMenuClick} />
                <main className="flex-1 overflow-y-auto overscroll-contain">
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/file-upload" element={<FileUpload />} />
                    <Route path="/semantic-search" element={<SemanticSearch />} />
                    <Route path="/agent-chat" element={<AgentChat />} />
                    <Route path="/data-generator" element={<DataGenerator />} />
                    <Route path="/visualization" element={<VisualizationDynamic />} />
                    <Route path="/visualization-old" element={<Visualization />} />
                    <Route path="/question-generator" element={<QuestionGenerator />} />
                    <Route path="/benchmarking" element={<Benchmarking />} />
                    <Route path="/prompt-engineering" element={<PromptEngineering />} />
                    <Route path="/comparison" element={<ComparisonAnalysis />} />
                    <Route path="/system-report" element={<SystemReport />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </main>
              </div>
            </div>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  )
}

export default App
