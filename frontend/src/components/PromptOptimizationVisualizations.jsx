import { useMemo } from "react"
import { FiBarChart2, FiTrendingUp, FiTrendingDown, FiMinus, FiCheckCircle, FiXCircle } from "react-icons/fi"

const PromptOptimizationVisualizations = ({ results }) => {
  // Process results data
  const processedData = useMemo(() => {
    if (!results || !results.report) {
      return null
    }

    const { report, detailed_results } = results

    // Group by category
    const byCategory = {}
    if (detailed_results && Array.isArray(detailed_results)) {
      detailed_results.forEach((item) => {
        const category = item.category || "Unknown"
        if (!byCategory[category]) {
          byCategory[category] = {
            category,
            count: 0,
            baseline: { overall: [], sql: [], table: [], methodology: [] },
            enhanced: { overall: [], sql: [], table: [], methodology: [] },
            improvements: { overall: [], sql: [], table: [], methodology: [] },
          }
        }
        byCategory[category].count++
        if (item.baseline) {
          if (item.baseline.overall_score !== undefined)
            byCategory[category].baseline.overall.push(item.baseline.overall_score)
          if (item.baseline.sql_score !== undefined)
            byCategory[category].baseline.sql.push(item.baseline.sql_score)
          if (item.baseline.table_column_score !== undefined)
            byCategory[category].baseline.table.push(item.baseline.table_column_score)
          if (item.baseline.methodology_score !== undefined)
            byCategory[category].baseline.methodology.push(item.baseline.methodology_score)
        }
        if (item.enhanced) {
          if (item.enhanced.overall_score !== undefined)
            byCategory[category].enhanced.overall.push(item.enhanced.overall_score)
          if (item.enhanced.sql_score !== undefined)
            byCategory[category].enhanced.sql.push(item.enhanced.sql_score)
          if (item.enhanced.table_column_score !== undefined)
            byCategory[category].enhanced.table.push(item.enhanced.table_column_score)
          if (item.enhanced.methodology_score !== undefined)
            byCategory[category].enhanced.methodology.push(item.enhanced.methodology_score)
        }
        if (item.improvements) {
          if (item.improvements.overall_improvement !== undefined)
            byCategory[category].improvements.overall.push(item.improvements.overall_improvement)
          if (item.improvements.sql_improvement !== undefined)
            byCategory[category].improvements.sql.push(item.improvements.sql_improvement)
          if (item.improvements.table_improvement !== undefined)
            byCategory[category].improvements.table.push(item.improvements.table_improvement)
          if (item.improvements.methodology_improvement !== undefined)
            byCategory[category].improvements.methodology.push(item.improvements.methodology_improvement)
        }
      })
    }

    const categoryStats = Object.values(byCategory).map((cat) => ({
      ...cat,
      avg_baseline_overall:
        cat.baseline.overall.length > 0
          ? cat.baseline.overall.reduce((a, b) => a + b, 0) / cat.baseline.overall.length
          : 0,
      avg_enhanced_overall:
        cat.enhanced.overall.length > 0
          ? cat.enhanced.overall.reduce((a, b) => a + b, 0) / cat.enhanced.overall.length
          : 0,
      avg_improvement_overall:
        cat.improvements.overall.length > 0
          ? cat.improvements.overall.reduce((a, b) => a + b, 0) / cat.improvements.overall.length
          : 0,
    }))

    return {
      report,
      categoryStats: categoryStats.sort((a, b) => b.avg_improvement_overall - a.avg_improvement_overall),
      detailedResults: detailed_results || [],
    }
  }, [results])

  if (!processedData) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p>No model optimization data available for visualization.</p>
        <p className="text-sm mt-2">Test enhanced prompts to see visualizations here.</p>
      </div>
    )
  }

  const { report, categoryStats, detailedResults } = processedData

  // Helper function to get color based on score
  const getScoreColor = (score) => {
    if (score >= 80) return "text-green-400"
    if (score >= 60) return "text-yellow-400"
    return "text-red-400"
  }

  const getBarColor = (score) => {
    if (score >= 80) return "bg-green-500"
    if (score >= 60) return "bg-yellow-500"
    return "bg-red-500"
  }

  const getImprovementColor = (improvement) => {
    if (improvement > 0) return "text-green-400"
    if (improvement < 0) return "text-red-400"
    return "text-gray-400"
  }

  const getImprovementBarColor = (improvement) => {
    if (improvement > 0) return "bg-green-500"
    if (improvement < 0) return "bg-red-500"
    return "bg-gray-500"
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-2">
            <FiBarChart2 className="h-5 w-5 text-blue-400 shrink-0" />
            <span className="text-sm text-gray-400">Total Questions</span>
          </div>
          <div className="text-2xl md:text-3xl font-bold text-gray-100 break-words">
            {report.total_questions || 0}
          </div>
        </div>

        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-2">
            <FiTrendingUp className="h-5 w-5 text-green-400 shrink-0" />
            <span className="text-sm text-gray-400">Improvement Rate</span>
          </div>
          <div className="text-2xl md:text-3xl font-bold text-green-400 break-words">
            {report.improvement_rate?.toFixed(1) || "0.0"}%
          </div>
        </div>

        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-2">
            <FiCheckCircle className="h-5 w-5 text-blue-400 shrink-0" />
            <span className="text-sm text-gray-400">Avg Overall Improvement</span>
          </div>
          <div className="text-2xl md:text-3xl font-bold text-gray-100 break-words">
            {report.average_improvements?.overall?.toFixed(1) || "0.0"}
            <span className="text-lg text-gray-400">%</span>
          </div>
        </div>

        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-2">
            <FiBarChart2 className="h-5 w-5 text-purple-400 shrink-0" />
            <span className="text-sm text-gray-400">Improved Questions</span>
          </div>
          <div className="text-2xl md:text-3xl font-bold text-green-400 break-words">
            {report.improved || 0}
            <span className="text-lg text-gray-400">/{report.total_questions || 0}</span>
          </div>
        </div>
      </div>

      {/* Baseline vs Enhanced Comparison */}
      <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg">
        <h3 className="text-xl font-semibold text-gray-100 mb-6 flex items-center gap-2">
          <FiBarChart2 className="h-5 w-5 text-blue-400" />
          Baseline vs Enhanced Prompts Comparison
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {["overall", "sql", "table", "methodology"].map((metric) => {
            const baselineKey = metric === "table" ? "table" : metric
            const enhancedKey = metric === "table" ? "table" : metric
            const improvementKey = metric === "table" ? "table" : metric

            const baseline = report.baseline_averages?.[baselineKey] || 0
            const enhanced = report.enhanced_averages?.[enhancedKey] || 0
            const improvement = report.average_improvements?.[improvementKey] || 0

            return (
              <div
                key={metric}
                className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4"
              >
                <h4 className="text-sm font-semibold text-gray-300 mb-4 capitalize">
                  {metric === "table" ? "Table/Column" : metric} Score
                </h4>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-400">Baseline</span>
                      <span className={`font-bold ${getScoreColor(baseline)}`}>
                        {baseline.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-2">
                      <div
                        className={`h-full ${getBarColor(baseline)}`}
                        style={{ width: `${Math.min(baseline, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-400">Enhanced</span>
                      <span className={`font-bold ${getScoreColor(enhanced)}`}>
                        {enhanced.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-2">
                      <div
                        className={`h-full ${getBarColor(enhanced)}`}
                        style={{ width: `${Math.min(enhanced, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="pt-2 border-t border-gray-700">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">Improvement</span>
                      <span className={`font-bold flex items-center gap-1 ${getImprovementColor(improvement)}`}>
                        {improvement > 0 ? (
                          <FiTrendingUp className="h-3 w-3" />
                        ) : improvement < 0 ? (
                          <FiTrendingDown className="h-3 w-3" />
                        ) : (
                          <FiMinus className="h-3 w-3" />
                        )}
                        {improvement > 0 ? "+" : ""}
                        {improvement.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Improvement Statistics */}
      <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg">
        <h3 className="text-xl font-semibold text-gray-100 mb-6 flex items-center gap-2">
          <FiTrendingUp className="h-5 w-5 text-green-400" />
          Improvement Statistics
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-800/50 border border-green-700/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <FiCheckCircle className="h-5 w-5 text-green-400" />
              <span className="text-sm font-semibold text-gray-300">Improved</span>
            </div>
            <div className="text-2xl font-bold text-green-400">
              {report.improved || 0}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {report.total_questions
                ? ((report.improved / report.total_questions) * 100).toFixed(1)
                : 0}
              % of questions
            </div>
          </div>

          <div className="bg-gray-800/50 border border-red-700/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <FiXCircle className="h-5 w-5 text-red-400" />
              <span className="text-sm font-semibold text-gray-300">Degraded</span>
            </div>
            <div className="text-2xl font-bold text-red-400">
              {report.degraded || 0}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {report.total_questions
                ? ((report.degraded / report.total_questions) * 100).toFixed(1)
                : 0}
              % of questions
            </div>
          </div>

          <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <FiMinus className="h-5 w-5 text-gray-400" />
              <span className="text-sm font-semibold text-gray-300">No Change</span>
            </div>
            <div className="text-2xl font-bold text-gray-400">
              {report.same || 0}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {report.total_questions
                ? ((report.same / report.total_questions) * 100).toFixed(1)
                : 0}
              % of questions
            </div>
          </div>
        </div>
      </div>

      {/* Category Breakdown */}
      {categoryStats.length > 0 && (
        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg">
          <h3 className="text-xl font-semibold text-gray-100 mb-6 flex items-center gap-2">
            <FiBarChart2 className="h-5 w-5 text-purple-400" />
            Performance by Question Category
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {categoryStats.map((cat) => (
              <div
                key={cat.category}
                className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4"
              >
                <h4 className="text-lg font-semibold text-gray-100 mb-4">{cat.category}</h4>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-400">Baseline</span>
                      <span className={`font-bold ${getScoreColor(cat.avg_baseline_overall)}`}>
                        {cat.avg_baseline_overall.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-2">
                      <div
                        className={`h-full ${getBarColor(cat.avg_baseline_overall)}`}
                        style={{ width: `${Math.min(cat.avg_baseline_overall, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-400">Enhanced</span>
                      <span className={`font-bold ${getScoreColor(cat.avg_enhanced_overall)}`}>
                        {cat.avg_enhanced_overall.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-2">
                      <div
                        className={`h-full ${getBarColor(cat.avg_enhanced_overall)}`}
                        style={{ width: `${Math.min(cat.avg_enhanced_overall, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="pt-2 border-t border-gray-700">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">Improvement</span>
                      <span
                        className={`font-bold flex items-center gap-1 ${getImprovementColor(cat.avg_improvement_overall)}`}
                      >
                        {cat.avg_improvement_overall > 0 ? (
                          <FiTrendingUp className="h-3 w-3" />
                        ) : cat.avg_improvement_overall < 0 ? (
                          <FiTrendingDown className="h-3 w-3" />
                        ) : (
                          <FiMinus className="h-3 w-3" />
                        )}
                        {cat.avg_improvement_overall > 0 ? "+" : ""}
                        {cat.avg_improvement_overall.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div className="pt-2 border-t border-gray-700 mt-2">
                    <span className="text-xs text-gray-400">Questions: {cat.count}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default PromptOptimizationVisualizations

