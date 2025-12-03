import { Link, useLocation } from "react-router-dom"
import { FiHome, FiBarChart2, FiX, FiChevronLeft, FiChevronRight, FiDatabase, FiTrendingUp, FiHelpCircle, FiCode, FiLayers, FiUpload, FiSearch, FiMessageCircle, FiFileText } from "react-icons/fi"

const Sidebar = ({ isOpen, onClose, isCollapsed, onToggleCollapse }) => {
  const location = useLocation()

  const menuSections = [
    {
      title: "🏠 Dashboard",
      items: [
        { path: "/", label: "Home", icon: FiHome }
      ]
    },
    {
      title: "📊 Phase 1: Data Generation",
      items: [
        { path: "/data-generator", label: "Data Generator", icon: FiDatabase }
      ]
    },
    {
      title: "❓ Phase 2: Question Generator",
      items: [
        { path: "/question-generator", label: "Question Generator", icon: FiHelpCircle }
      ]
    },
    {
      title: "🤖 Phase 3: Model Selection & Optimization",
      items: [
        { path: "/benchmarking", label: "LLM Benchmarking", icon: FiBarChart2 },
        { path: "/prompt-engineering", label: "Prompt Engineering", icon: FiCode }
      ]
    },
    {
      title: "🔍 Phase 4: Data Management & Search",
      items: [
        { path: "/file-upload", label: "File Upload", icon: FiUpload },
        { path: "/semantic-search", label: "Semantic Search", icon: FiSearch }
      ]
    },
    {
      title: "💬 Phase 5: AI Agent & Visualization",
      items: [
        { path: "/agent-chat", label: "AI Agent Chat", icon: FiMessageCircle },
        { path: "/visualization", label: "Visualizations", icon: FiTrendingUp }
      ]
    },
    {
      title: "📈 Phase 6: Evaluation & Analysis",
      items: [
        { path: "/comparison", label: "Comparison Analysis", icon: FiLayers }
      ]
    },
    {
      title: "⚙️ System Management",
      items: [
        { path: "/system-report", label: "System Report", icon: FiFileText }
      ]
    }
  ]

  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      onClose()
    }
  }

  const handleCollapseKeyDown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      onToggleCollapse()
    }
  }

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
          onKeyDown={handleKeyDown}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-screen z-50 transition-all duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0 lg:z-auto`}
        aria-label="Sidebar navigation"
      >
        <div
          className={`h-full bg-gray-900/80 backdrop-blur-xl border-r border-gray-800/50 shadow-2xl flex flex-col transition-all duration-300 ${
            isCollapsed ? "w-20" : "w-64"
          }`}
        >
          {/* Sidebar Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-800/50">
            {!isCollapsed && (
              <h2 className="text-xl font-bold text-gray-100 whitespace-nowrap">ExcelLLM</h2>
            )}
            <div className="flex items-center gap-2 ml-auto">
              {/* Collapse Toggle Button - Desktop */}
              <button
                onClick={onToggleCollapse}
                onKeyDown={handleCollapseKeyDown}
                className="hidden lg:inline-flex items-center justify-center rounded-md p-2 text-gray-400 hover:bg-white/10 hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-700 transition-colors"
                aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                tabIndex={0}
              >
                {isCollapsed ? (
                  <FiChevronRight className="h-5 w-5" aria-hidden="true" />
                ) : (
                  <FiChevronLeft className="h-5 w-5" aria-hidden="true" />
                )}
              </button>
              {/* Close Button - Mobile */}
              <button
                onClick={onClose}
                onKeyDown={handleKeyDown}
                className="lg:hidden inline-flex items-center justify-center rounded-md p-2 text-gray-400 hover:bg-white/10 hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-700 transition-colors"
                aria-label="Close sidebar"
                tabIndex={0}
              >
                <FiX className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
          </div>

          {/* Navigation Menu */}
          <nav className="flex-1 p-4 space-y-4 overflow-y-auto">
            {menuSections.map((section, sectionIndex) => (
              <div key={sectionIndex} className="space-y-2">
                {/* Section Header */}
                {!isCollapsed && (
                  <h3 className="px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    {section.title}
                  </h3>
                )}
                {isCollapsed && sectionIndex > 0 && (
                  <div className="border-t border-gray-800/50 my-2"></div>
                )}
                
                {/* Section Items */}
                {section.items.map((item) => {
                  const Icon = item.icon
                  const isActive = location.pathname === item.path

                  return (
                    <div key={item.path} className="relative">
                      <Link
                        to={item.path}
                        onClick={() => {
                          // Only close sidebar on mobile devices
                          if (window.innerWidth < 1024) {
                            onClose()
                          }
                        }}
                        className={`flex items-center gap-3 px-4 py-3 rounded-lg text-gray-300 transition-all duration-200 group ${
                          isActive
                            ? "bg-white/10 text-white shadow-lg backdrop-blur-sm border border-white/20"
                            : "hover:bg-white/5 hover:text-gray-100"
                        } ${isCollapsed ? "justify-center" : ""}`}
                        tabIndex={0}
                        title={isCollapsed ? item.label : ""}
                      >
                        <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                        {!isCollapsed && (
                          <span className="font-medium whitespace-nowrap">{item.label}</span>
                        )}
                      </Link>
                      {/* Tooltip for collapsed state */}
                      {isCollapsed && (
                        <span className="absolute left-full ml-2 px-3 py-2 bg-gray-800/95 backdrop-blur-sm text-gray-100 text-sm rounded shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 transition-opacity border border-gray-700">
                          {item.label}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            ))}
          </nav>

          {/* Sidebar Footer */}
          <div className="p-4 border-t border-gray-800/50">
            {!isCollapsed && (
              <div className="px-4 py-2 text-sm text-gray-400">
                <p>Version 1.0.0</p>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar

