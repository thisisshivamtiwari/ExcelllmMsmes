import { useMemo } from "react"
import { FiBarChart2, FiTrendingUp, FiClock, FiCheckCircle, FiXCircle } from "react-icons/fi"

const BenchmarkVisualizations = ({ results }) => {
  // Process results data
  const processedData = useMemo(() => {
    // Handle different result structures
    let data = null
    if (Array.isArray(results)) {
      data = results
    } else if (results && Array.isArray(results.results)) {
      data = results.results
    } else if (results && results.by_model) {
      // If it's already processed summary data
      return {
        modelStats: Object.values(results.by_model).map((model) => ({
          model_id: model.model_id || Object.keys(results.by_model).find(k => results.by_model[k] === model),
          ...model,
        })),
        categoryStats: results.by_category ? Object.values(results.by_category).map((cat) => ({
          category: cat.category || Object.keys(results.by_category).find(k => results.by_category[k] === cat),
          ...cat,
        })) : [],
        totalEvaluations: results.total_evaluations || 0,
        totalModels: results.models_evaluated?.length || 0,
      }
    }

    if (!data || !Array.isArray(data) || data.length === 0) {
      return null
    }

    // Group by model
    const byModel = {}
    data.forEach((item) => {
      const modelId = item.model_id || "unknown"
      if (!byModel[modelId]) {
        byModel[modelId] = {
          model_id: modelId,
          count: 0,
          scores: {
            overall: [],
            sql: [],
            table_column: [],
            methodology: [],
            response_quality: [],
          },
          latencies: [],
          errors: 0,
        }
      }
      byModel[modelId].count++
      if (item.overall_score !== undefined) byModel[modelId].scores.overall.push(item.overall_score)
      if (item.sql_score !== undefined) byModel[modelId].scores.sql.push(item.sql_score)
      if (item.table_column_score !== undefined)
        byModel[modelId].scores.table_column.push(item.table_column_score)
      if (item.methodology_score !== undefined)
        byModel[modelId].scores.methodology.push(item.methodology_score)
      if (item.response_quality_score !== undefined)
        byModel[modelId].scores.response_quality.push(item.response_quality_score)
      if (item.total_latency_ms !== undefined) byModel[modelId].latencies.push(item.total_latency_ms)
      if (item.errors && item.errors.length > 0) byModel[modelId].errors++
    })

    // Calculate averages
    const modelStats = Object.values(byModel).map((model) => ({
      ...model,
      avg_overall: model.scores.overall.length
        ? model.scores.overall.reduce((a, b) => a + b, 0) / model.scores.overall.length
        : 0,
      avg_sql: model.scores.sql.length
        ? model.scores.sql.reduce((a, b) => a + b, 0) / model.scores.sql.length
        : 0,
      avg_table_column: model.scores.table_column.length
        ? model.scores.table_column.reduce((a, b) => a + b, 0) / model.scores.table_column.length
        : 0,
      avg_methodology: model.scores.methodology.length
        ? model.scores.methodology.reduce((a, b) => a + b, 0) / model.scores.methodology.length
        : 0,
      avg_response_quality: model.scores.response_quality.length
        ? model.scores.response_quality.reduce((a, b) => a + b, 0) / model.scores.response_quality.length
        : 0,
      avg_latency_ms: model.latencies.length
        ? model.latencies.reduce((a, b) => a + b, 0) / model.latencies.length
        : 0,
    }))

    // Group by category
    const byCategory = {}
    data.forEach((item) => {
      const category = item.category || "Unknown"
      if (!byCategory[category]) {
        byCategory[category] = {
          category,
          count: 0,
          scores: {
            overall: [],
            sql: [],
            table_column: [],
            methodology: [],
          },
        }
      }
      byCategory[category].count++
      if (item.overall_score !== undefined) byCategory[category].scores.overall.push(item.overall_score)
      if (item.sql_score !== undefined) byCategory[category].scores.sql.push(item.sql_score)
      if (item.table_column_score !== undefined)
        byCategory[category].scores.table_column.push(item.table_column_score)
      if (item.methodology_score !== undefined)
        byCategory[category].scores.methodology.push(item.methodology_score)
    })

    const categoryStats = Object.values(byCategory).map((cat) => ({
      ...cat,
      avg_overall: cat.scores.overall.length
        ? cat.scores.overall.reduce((a, b) => a + b, 0) / cat.scores.overall.length
        : 0,
      avg_sql: cat.scores.sql.length
        ? cat.scores.sql.reduce((a, b) => a + b, 0) / cat.scores.sql.length
        : 0,
      avg_table_column: cat.scores.table_column.length
        ? cat.scores.table_column.reduce((a, b) => a + b, 0) / cat.scores.table_column.length
        : 0,
      avg_methodology: cat.scores.methodology.length
        ? cat.scores.methodology.reduce((a, b) => a + b, 0) / cat.scores.methodology.length
        : 0,
    }))

    return {
      modelStats: modelStats.sort((a, b) => b.avg_overall - a.avg_overall),
      categoryStats: categoryStats.sort((a, b) => b.avg_overall - a.avg_overall),
      totalEvaluations: data.length,
      totalModels: Object.keys(byModel).length,
    }
  }, [results])

  if (!processedData) {
    return (
      <div className="py-12 text-center text-gray-400">
        <p>No benchmark data available for visualization.</p>
        <p className="mt-2 text-sm">Run a benchmark to see visualizations here.</p>
      </div>
    )
  }

  const { modelStats, categoryStats, totalEvaluations, totalModels } = processedData

  // Helper function to format model names
  const formatModelName = (modelId) => {
    return modelId
      .split("/")
      .pop()
      .replace(/-/g, " ")
      .replace(/_/g, " ")
      .split(" ")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  }

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

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="p-4 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50 md:p-6">
          <div className="flex gap-3 items-center mb-2">
            <FiBarChart2 className="w-5 h-5 text-blue-400 shrink-0" />
            <span className="text-sm text-gray-400">Total Evaluations</span>
          </div>
          <div className="text-2xl font-bold text-gray-100 md:text-3xl wrap-break-word">{totalEvaluations.toLocaleString()}</div>
        </div>

        <div className="p-4 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50 md:p-6">
          <div className="flex gap-3 items-center mb-2">
            <FiTrendingUp className="w-5 h-5 text-green-400 shrink-0" />
            <span className="text-sm text-gray-400">Models Evaluated</span>
          </div>
          <div className="text-2xl font-bold text-gray-100 md:text-3xl wrap-break-word">{totalModels}</div>
        </div>

        <div className="p-4 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50 md:p-6">
          <div className="flex gap-3 items-center mb-2">
            <FiCheckCircle className="w-5 h-5 text-blue-400 shrink-0" />
            <span className="text-sm text-gray-400">Avg Overall Score</span>
          </div>
          <div className="text-2xl font-bold text-gray-100 md:text-3xl wrap-break-word">
            {modelStats.length > 0
              ? (
                  modelStats.reduce((sum, m) => sum + m.avg_overall, 0) / modelStats.length
                ).toFixed(1)
              : "0.0"}
            <span className="text-lg text-gray-400">%</span>
          </div>
        </div>

        <div className="p-4 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50 md:p-6">
          <div className="flex gap-3 items-center mb-2">
            <FiClock className="w-5 h-5 text-purple-400 shrink-0" />
            <span className="text-sm text-gray-400">Avg Latency</span>
          </div>
          <div className="text-2xl font-bold text-gray-100 md:text-3xl wrap-break-word">
            {modelStats.length > 0
              ? (
                  modelStats.reduce((sum, m) => sum + m.avg_latency_ms, 0) / modelStats.length / 1000
                ).toFixed(1)
              : "0.0"}
            <span className="text-lg text-gray-400">s</span>
          </div>
        </div>
      </div>

      {/* Model Comparison - Overall Scores */}
      <div className="p-4 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50 md:p-6">
        <h3 className="flex gap-2 items-center mb-6 text-xl font-semibold text-gray-100">
          <FiBarChart2 className="w-5 h-5 text-blue-400" />
          Model Performance Comparison
        </h3>
        <div className="space-y-4">
          {modelStats.map((model) => (
            <div key={model.model_id} className="space-y-2">
              <div className="flex gap-2 justify-between items-center text-sm">
                <span className="flex-1 min-w-0 font-medium text-gray-300 truncate">{formatModelName(model.model_id)}</span>
                <span className={`font-bold ${getScoreColor(model.avg_overall)} shrink-0`}>
                  {model.avg_overall.toFixed(1)}%
                </span>
              </div>
              <div className="overflow-hidden w-full h-3 rounded-full bg-gray-800/50">
                <div
                  className={`h-full ${getBarColor(model.avg_overall)} transition-all duration-500`}
                  style={{ width: `${Math.min(model.avg_overall, 100)}%` }}
                />
              </div>
              <div className="grid grid-cols-2 gap-2 mt-1 text-xs text-gray-400 md:grid-cols-4">
                <span className="truncate" title={`SQL: ${model.avg_sql.toFixed(1)}%`}>SQL: {model.avg_sql.toFixed(1)}%</span>
                <span className="truncate" title={`Table/Col: ${model.avg_table_column.toFixed(1)}%`}>Table/Col: {model.avg_table_column.toFixed(1)}%</span>
                <span className="truncate" title={`Methodology: ${model.avg_methodology.toFixed(1)}%`}>Methodology: {model.avg_methodology.toFixed(1)}%</span>
                <span className="truncate" title={`Latency: ${(model.avg_latency_ms / 1000).toFixed(1)}s`}>Latency: {(model.avg_latency_ms / 1000).toFixed(1)}s</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detailed Model Scores - Radar-like visualization */}
      <div className="p-4 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50 md:p-6">
        <h3 className="flex gap-2 items-center mb-6 text-xl font-semibold text-gray-100">
          <FiTrendingUp className="w-5 h-5 text-green-400" />
          Detailed Score Breakdown by Model
        </h3>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {modelStats.map((model) => (
            <div
              key={model.model_id}
              className="p-4 rounded-lg border bg-gray-800/50 border-gray-700/50"
            >
              <h4 className="mb-4 text-lg font-semibold text-gray-100">
                {formatModelName(model.model_id)}
              </h4>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between mb-1 text-sm">
                    <span className="text-gray-400">Overall Score</span>
                    <span className={`font-bold ${getScoreColor(model.avg_overall)}`}>
                      {model.avg_overall.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full">
                    <div
                      className={`h-full ${getBarColor(model.avg_overall)}`}
                      style={{ width: `${Math.min(model.avg_overall, 100)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1 text-sm">
                    <span className="text-gray-400">SQL Score</span>
                    <span className={`font-bold ${getScoreColor(model.avg_sql)}`}>
                      {model.avg_sql.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full">
                    <div
                      className={`h-full ${getBarColor(model.avg_sql)}`}
                      style={{ width: `${Math.min(model.avg_sql, 100)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1 text-sm">
                    <span className="text-gray-400">Table/Column Score</span>
                    <span className={`font-bold ${getScoreColor(model.avg_table_column)}`}>
                      {model.avg_table_column.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full">
                    <div
                      className={`h-full ${getBarColor(model.avg_table_column)}`}
                      style={{ width: `${Math.min(model.avg_table_column, 100)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1 text-sm">
                    <span className="text-gray-400">Methodology Score</span>
                    <span className={`font-bold ${getScoreColor(model.avg_methodology)}`}>
                      {model.avg_methodology.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full">
                    <div
                      className={`h-full ${getBarColor(model.avg_methodology)}`}
                      style={{ width: `${Math.min(model.avg_methodology, 100)}%` }}
                    />
                  </div>
                </div>
                {model.avg_response_quality > 0 && (
                  <div>
                    <div className="flex justify-between mb-1 text-sm">
                      <span className="text-gray-400">Response Quality</span>
                      <span className={`font-bold ${getScoreColor(model.avg_response_quality)}`}>
                        {model.avg_response_quality.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-gray-800 rounded-full">
                      <div
                        className={`h-full ${getBarColor(model.avg_response_quality)}`}
                        style={{ width: `${Math.min(model.avg_response_quality, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
                <div className="pt-2 mt-2 border-t border-gray-700">
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>Avg Latency: {(model.avg_latency_ms / 1000).toFixed(2)}s</span>
                    <span>Evaluations: {model.count}</span>
                    {model.errors > 0 && (
                      <span className="flex gap-1 items-center text-red-400">
                        <FiXCircle className="w-3 h-3" />
                        {model.errors} errors
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="p-4 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50 md:p-6">
        <h3 className="flex gap-2 items-center mb-6 text-xl font-semibold text-gray-100">
          <FiBarChart2 className="w-5 h-5 text-purple-400" />
          Performance by Question Category
        </h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {categoryStats.map((cat) => (
            <div
              key={cat.category}
              className="p-4 rounded-lg border bg-gray-800/50 border-gray-700/50"
            >
              <h4 className="mb-4 text-lg font-semibold text-gray-100">{cat.category}</h4>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between mb-1 text-sm">
                    <span className="text-gray-400">Overall</span>
                    <span className={`font-bold ${getScoreColor(cat.avg_overall)}`}>
                      {cat.avg_overall.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full">
                    <div
                      className={`h-full ${getBarColor(cat.avg_overall)}`}
                      style={{ width: `${Math.min(cat.avg_overall, 100)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1 text-sm">
                    <span className="text-gray-400">SQL</span>
                    <span className={`font-bold ${getScoreColor(cat.avg_sql)}`}>
                      {cat.avg_sql.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full">
                    <div
                      className={`h-full ${getBarColor(cat.avg_sql)}`}
                      style={{ width: `${Math.min(cat.avg_sql, 100)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1 text-sm">
                    <span className="text-gray-400">Table/Column</span>
                    <span className={`font-bold ${getScoreColor(cat.avg_table_column)}`}>
                      {cat.avg_table_column.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full">
                    <div
                      className={`h-full ${getBarColor(cat.avg_table_column)}`}
                      style={{ width: `${Math.min(cat.avg_table_column, 100)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1 text-sm">
                    <span className="text-gray-400">Methodology</span>
                    <span className={`font-bold ${getScoreColor(cat.avg_methodology)}`}>
                      {cat.avg_methodology.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full">
                    <div
                      className={`h-full ${getBarColor(cat.avg_methodology)}`}
                      style={{ width: `${Math.min(cat.avg_methodology, 100)}%` }}
                    />
                  </div>
                </div>
                <div className="pt-2 mt-2 border-t border-gray-700">
                  <span className="text-xs text-gray-400">Questions: {cat.count}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default BenchmarkVisualizations

