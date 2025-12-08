import { useState, useRef, useEffect } from "react"
import { FiMenu, FiUser, FiLogOut, FiChevronDown } from "react-icons/fi"
import { useAuth } from "@/contexts/AuthContext"
import { useNavigate } from "react-router-dom"

const Header = ({ onMenuClick }) => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const menuRef = useRef(null)

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setUserMenuOpen(false)
      }
    }

    if (userMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside)
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [userMenuOpen])

  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      onMenuClick?.()
    }
  }

  const handleLogout = () => {
    logout()
    navigate("/login")
    setUserMenuOpen(false)
  }

  return (
    <header className="sticky top-0 z-30 w-full border-b border-gray-800/50 bg-gray-950/80 backdrop-blur-xl">
      <div className="flex h-16 items-center justify-between px-4 md:px-6 lg:px-8">
        <div className="flex items-center">
          {/* Menu Toggle Button - Mobile Only */}
          <button
            onClick={onMenuClick}
            onKeyDown={handleKeyDown}
            className="lg:hidden inline-flex items-center justify-center rounded-lg p-2 text-gray-400 hover:bg-white/10 hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-700 transition-all duration-200 mr-4"
            aria-label="Toggle sidebar"
            tabIndex={0}
          >
            <FiMenu className="h-6 w-6" aria-hidden="true" />
          </button>

          {/* Logo/Brand */}
          <h1 className="text-xl font-bold text-gray-100">ExcelLLM</h1>
        </div>

        {/* User Menu */}
        {user && (
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-300 hover:bg-gray-800/50 transition"
              aria-label="User menu"
            >
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                  <FiUser className="text-white text-sm" />
                </div>
                <span className="hidden md:block text-sm font-medium">
                  {user.name || user.email.split("@")[0]}
                </span>
                <FiChevronDown className="hidden md:block text-gray-400" />
              </div>
            </button>

            {/* Dropdown Menu */}
            {userMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-gray-800 border border-gray-700 rounded-lg shadow-xl py-2 z-50">
                {/* User Info */}
                <div className="px-4 py-3 border-b border-gray-700">
                  <p className="text-sm font-medium text-white">
                    {user.name || "User"}
                  </p>
                  <p className="text-xs text-gray-400 truncate">{user.email}</p>
                  {user.industry && (
                    <p className="text-xs text-gray-500 mt-1">
                      Industry: {user.industry}
                    </p>
                  )}
                </div>

                {/* Logout Button */}
                <button
                  onClick={handleLogout}
                  className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-gray-700/50 transition flex items-center gap-2"
                >
                  <FiLogOut />
                  <span>Sign Out</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  )
}

export default Header
