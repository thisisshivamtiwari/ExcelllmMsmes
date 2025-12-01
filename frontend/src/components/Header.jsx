import { FiMenu } from "react-icons/fi"

const Header = ({ onMenuClick }) => {
  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      onMenuClick?.()
    }
  }

  return (
    <header className="sticky top-0 z-30 w-full border-b border-gray-800/50 bg-gray-950/80 backdrop-blur-xl">
      <div className="flex h-16 items-center px-4 md:px-6 lg:px-8">
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
        <div className="flex items-center">
          <h1 className="text-xl font-bold text-gray-100">ExcelLLM</h1>
        </div>
      </div>
    </header>
  )
}

export default Header
