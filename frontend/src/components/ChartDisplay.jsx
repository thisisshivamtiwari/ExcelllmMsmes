import { useMemo } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Bar, Line, Pie, Doughnut, Radar, PolarArea, Scatter, Bubble } from 'react-chartjs-2'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler
)

/**
 * ChartDisplay Component
 * Renders Chart.js charts from JSON configuration returned by the GraphGenerator tool
 * 
 * @param {Object} chartConfig - Chart.js configuration object with type, data, and options
 */
const ChartDisplay = ({ chartConfig }) => {
  // Parse chartConfig if it's a string (handles double-encoded JSON)
  const config = useMemo(() => {
    try {
      let parsed = chartConfig
      
      // Handle string input - may be double-encoded
      if (typeof chartConfig === 'string') {
        try {
          parsed = JSON.parse(chartConfig)
          // Check if we got another string (double-encoded)
          if (typeof parsed === 'string') {
            parsed = JSON.parse(parsed)
          }
        } catch (error) {
          console.error('Failed to parse chart config:', error)
          return null
        }
      }
      
      // Validate required fields
      if (!parsed || typeof parsed !== 'object') {
        console.error('Chart config is not an object:', typeof parsed)
        return null
      }
      
      if (!parsed.type && !parsed.chart_type) {
        console.error('Chart config missing type field')
        return null
      }
      
      if (!parsed.data) {
        console.error('Chart config missing data field')
        return null
      }
      
      // Normalize: chart_type -> type
      if (parsed.chart_type && !parsed.type) {
        parsed.type = parsed.chart_type
      }
      
      console.log('✅ Chart config validated:', { type: parsed.type, hasData: !!parsed.data })
      return parsed
    } catch (error) {
      console.error('Error in chart config processing:', error)
      return null
    }
  }, [chartConfig])

  if (!config || !config.type || !config.data) {
    console.log('❌ Chart render blocked - invalid config')
    return (
      <div className="p-4 bg-red-900/20 border border-red-700/50 rounded-lg">
        <p className="text-red-400 text-sm">Invalid chart configuration</p>
        {chartConfig && <p className="text-red-300 text-xs mt-1">Check console for details</p>}
      </div>
    )
  }

  const chartType = config.type.toLowerCase()
  const chartData = config.data
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    ...config.options,
    plugins: {
      legend: {
        labels: {
          color: '#e5e7eb', // text-gray-200
          font: {
            size: 12
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(17, 24, 39, 0.95)', // gray-900
        titleColor: '#f3f4f6', // gray-100
        bodyColor: '#e5e7eb', // gray-200
        borderColor: '#374151', // gray-700
        borderWidth: 1,
        padding: 12,
        displayColors: true,
        ...config.options?.plugins?.tooltip
      },
      title: {
        display: true,
        color: '#f9fafb', // gray-50
        font: {
          size: 16,
          weight: 'bold'
        },
        ...config.options?.plugins?.title
      },
      ...config.options?.plugins
    },
    scales: config.options?.scales ? {
      x: {
        ticks: {
          color: '#9ca3af', // gray-400
          font: {
            size: 11
          }
        },
        grid: {
          color: 'rgba(75, 85, 99, 0.2)', // gray-600 with opacity
          borderColor: '#4b5563' // gray-600
        },
        ...config.options.scales.x
      },
      y: {
        ticks: {
          color: '#9ca3af', // gray-400
          font: {
            size: 11
          }
        },
        grid: {
          color: 'rgba(75, 85, 99, 0.2)', // gray-600 with opacity
          borderColor: '#4b5563' // gray-600
        },
        ...config.options.scales.y
      }
    } : undefined
  }

  // Render appropriate chart component based on type
  const renderChart = () => {
    const commonProps = {
      data: chartData,
      options: chartOptions
    }

    switch (chartType) {
      case 'bar':
      case 'stacked_bar':
      case 'grouped_bar':
        return <Bar {...commonProps} />
      
      case 'line':
      case 'multi_line':
        return <Line {...commonProps} />
      
      case 'area':
        return <Line {...commonProps} />
      
      case 'pie':
        return <Pie {...commonProps} />
      
      case 'doughnut':
        return <Doughnut {...commonProps} />
      
      case 'radar':
        return <Radar {...commonProps} />
      
      case 'polararea':
        return <PolarArea {...commonProps} />
      
      case 'scatter':
        return <Scatter {...commonProps} />
      
      case 'bubble':
        return <Bubble {...commonProps} />
      
      case 'combo':
        // Combo charts use Bar component with mixed dataset types
        return <Bar {...commonProps} />
      
      default:
        return (
          <div className="p-4 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
            <p className="text-yellow-400 text-sm">
              Unsupported chart type: {chartType}
            </p>
          </div>
        )
    }
  }

  try {
    return (
      <div className="w-full bg-gradient-to-br from-gray-900 to-gray-850 border border-gray-700/50 rounded-2xl p-6 my-4 shadow-2xl">
        {/* Chart Title */}
        {config.title && (
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="text-2xl">📊</span>
            {config.title}
          </h3>
        )}
        
        {/* Chart Container - Bigger */}
        <div className="w-full bg-gray-800/30 rounded-xl p-4" style={{ minHeight: '450px', maxHeight: '650px' }}>
          {renderChart()}
        </div>
        
        {/* Chart metadata */}
        <div className="mt-4 pt-4 border-t border-gray-700/30 flex items-center justify-between text-xs text-gray-400">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-400"></span>
            Chart Type: <span className="text-blue-300 font-medium">{chartType}</span>
          </span>
          {chartData.datasets && (
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-400"></span>
              {chartData.datasets.length} dataset{chartData.datasets.length !== 1 ? 's' : ''}
            </span>
          )}
          {chartData.labels && (
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-400"></span>
              {chartData.labels.length} data point{chartData.labels.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>
    )
  } catch (error) {
    console.error('❌ Chart render error:', error)
    return (
      <div className="p-4 bg-red-900/20 border border-red-700/50 rounded-lg">
        <p className="text-red-400 text-sm font-semibold">Chart Rendering Error</p>
        <p className="text-red-300 text-xs mt-1">{error.message}</p>
        <details className="mt-2">
          <summary className="text-xs text-red-400 cursor-pointer">Details</summary>
          <pre className="text-xs text-red-300 mt-1 overflow-auto">{error.stack}</pre>
        </details>
      </div>
    )
  }
}

export default ChartDisplay
