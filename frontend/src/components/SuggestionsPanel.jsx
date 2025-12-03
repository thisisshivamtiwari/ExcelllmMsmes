import { useState } from 'react'
import { FiChevronDown, FiChevronUp, FiBarChart2 } from 'react-icons/fi'

/**
 * SuggestionsPanel Component
 * Displays persistent dropdown with 25+ pre-populated graph questions
 * Organized by category for easy navigation
 */
const SuggestionsPanel = ({ onSelectQuestion, disabled }) => {
  const [isExpanded, setIsExpanded] = useState(false) // Collapsed by default
  const [selectedCategory, setSelectedCategory] = useState('all')

  // All 25+ test questions organized by category
  const questionCategories = {
    'Production Trends': [
      'Show me daily production trend as a line chart',
      'Create a bar chart of production quantity by product',
      'Show production actual vs target quantities as a grouped bar chart',
      'Display production by shift as a pie chart',
      'Show weekly production trends as an area chart'
    ],
    'Quality Analysis': [
      'Show defect distribution by type as a pie chart',
      'Create a line chart showing pass/fail rates over time',
      'Display defect types comparison as a bar chart',
      'Show quality metrics by inspector as a radar chart',
      'Create a stacked bar chart of passed vs failed quantities by line'
    ],
    'Maintenance Analysis': [
      'Show maintenance costs by machine as a bar chart',
      'Display downtime trends over time as a line chart',
      'Create a pie chart of maintenance types distribution',
      'Show maintenance cost vs downtime as a scatter plot'
    ],
    'Inventory Analysis': [
      'Show material consumption trends as an area chart',
      'Display wastage by material as a bar chart',
      'Create a multi-line chart showing stock levels for all materials',
      'Show material cost distribution as a pie chart'
    ],
    'Cross-File Relationships': [
      'Create a combo chart showing production vs quality over time',
      'Display efficiency radar chart comparing all metrics',
      'Show maintenance impact on production as a scatter plot',
      'Create a combo chart of material consumption vs production output'
    ],
    'KPI Dashboards': [
      'Show OEE by machine as a bar chart',
      'Display FPY trends over time as a line chart',
      'Create a radar chart showing all KPIs together'
    ],
    'Edge Cases': [
      'Show data for a specific date range with limited data',
      'Create a chart for a single product or machine'
    ]
  }

  const allQuestions = Object.values(questionCategories).flat()

  const filteredQuestions = selectedCategory === 'all' 
    ? allQuestions 
    : questionCategories[selectedCategory]

  const handleQuestionClick = (question) => {
    onSelectQuestion(question)
  }

  return (
    <div className="w-full mb-4">
      <div className="bg-gray-800/50 backdrop-blur-xl border border-gray-700/50 rounded-xl overflow-hidden">
        {/* Header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between p-4 hover:bg-gray-800/70 transition-colors"
          disabled={disabled}
        >
          <div className="flex items-center gap-2">
            <FiBarChart2 className="text-blue-400" />
            <span className="text-white font-medium">Graph Suggestions</span>
            <span className="text-xs text-gray-500 bg-gray-700/50 px-2 py-1 rounded">
              {allQuestions.length} questions
            </span>
          </div>
          {isExpanded ? (
            <FiChevronUp className="text-gray-400" />
          ) : (
            <FiChevronDown className="text-gray-400" />
          )}
        </button>

        {/* Expanded Content */}
        {isExpanded && (
          <div className="border-t border-gray-700/50">
            {/* Category Filter */}
            <div className="p-3 bg-gray-900/50 border-b border-gray-700/50 overflow-x-auto">
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => setSelectedCategory('all')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                    selectedCategory === 'all'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700'
                  }`}
                  disabled={disabled}
                >
                  All ({allQuestions.length})
                </button>
                {Object.keys(questionCategories).map((category) => (
                  <button
                    key={category}
                    onClick={() => setSelectedCategory(category)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                      selectedCategory === category
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700'
                    }`}
                    disabled={disabled}
                  >
                    {category} ({questionCategories[category].length})
                  </button>
                ))}
              </div>
            </div>

            {/* Questions List */}
            <div className="p-3 max-h-64 overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {filteredQuestions.map((question, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleQuestionClick(question)}
                    className="text-left p-3 rounded-lg bg-gray-700/30 hover:bg-gray-700/60 border border-gray-600/30 hover:border-blue-500/50 transition-all text-sm text-gray-300 hover:text-white group"
                    disabled={disabled}
                  >
                    <div className="flex items-start gap-2">
                      <span className="text-blue-400 opacity-50 group-hover:opacity-100 transition-opacity">
                        •
                      </span>
                      <span className="flex-1">{question}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Footer with category info */}
            {selectedCategory !== 'all' && (
              <div className="p-3 bg-gray-900/50 border-t border-gray-700/50 text-xs text-gray-500">
                Showing {filteredQuestions.length} questions in {selectedCategory}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default SuggestionsPanel
