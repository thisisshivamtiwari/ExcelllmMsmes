import { useState, useEffect } from "react"
import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import Header from "@/components/Header"
import Sidebar from "@/components/Sidebar"
import Dashboard from "@/pages/Dashboard"
import DataGenerator from "@/pages/DataGenerator"
import Visualization from "@/pages/Visualization"
import QuestionGenerator from "@/pages/QuestionGenerator"
import Benchmarking from "@/pages/Benchmarking"
import PromptEngineering from "@/pages/PromptEngineering"
import ComparisonAnalysis from "@/pages/ComparisonAnalysis"
import FileUpload from "@/pages/FileUpload"
import Analytics from "@/pages/Analytics"
import Reports from "@/pages/Reports"
import Settings from "@/pages/Settings"

function App() {
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
    <Router>
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
              <Route path="/data-generator" element={<DataGenerator />} />
              <Route path="/visualization" element={<Visualization />} />
              <Route path="/question-generator" element={<QuestionGenerator />} />
              <Route path="/benchmarking" element={<Benchmarking />} />
              <Route path="/prompt-engineering" element={<PromptEngineering />} />
              <Route path="/comparison" element={<ComparisonAnalysis />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  )
}

export default App
