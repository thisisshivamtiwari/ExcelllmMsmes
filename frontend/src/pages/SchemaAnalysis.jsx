import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { 
  FiDatabase, 
  FiBarChart2, 
  FiPieChart, 
  FiTrendingUp, 
  FiCheckCircle, 
  FiAlertCircle,
  FiLink,
  FiType,
  FiLayers
} from 'react-icons/fi';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

// Get API base URL and normalize it
const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  // Remove trailing /api if present to avoid double /api/api
  return envUrl.endsWith('/api') ? envUrl.slice(0, -4) : envUrl;
};

const API_BASE_URL = getApiBaseUrl();

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'];

const SchemaAnalysis = () => {
  const { fileId } = useParams();
  const [loading, setLoading] = useState(true);
  const [schemaData, setSchemaData] = useState(null);
  const [visualizationData, setVisualizationData] = useState(null);
  const [error, setError] = useState(null);
  const [selectedSheet, setSelectedSheet] = useState(null);

  useEffect(() => {
    if (fileId) {
      fetchSchemaAnalysis();
    }
  }, [fileId]);

  const fetchSchemaAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/api/schema/analyze/${fileId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch schema analysis: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSchemaData(data.schema);
      setVisualizationData(data.visualization);
      
      // Set first sheet as selected
      if (data.schema?.sheets) {
        const firstSheet = Object.keys(data.schema.sheets)[0];
        setSelectedSheet(firstSheet);
      }
    } catch (err) {
      console.error('Error fetching schema analysis:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-400">Analyzing schema...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-6 text-red-400">
            <div className="flex items-center gap-2 mb-2">
              <FiAlertCircle className="w-5 h-5" />
              <h3 className="text-lg font-semibold">Error</h3>
            </div>
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!schemaData || !visualizationData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <p className="text-gray-400">No schema data available</p>
        </div>
      </div>
    );
  }

  const currentSheet = selectedSheet ? schemaData.sheets[selectedSheet] : null;
  const typeDistribution = selectedSheet && visualizationData.type_distribution[selectedSheet]
    ? Object.entries(visualizationData.type_distribution[selectedSheet]).map(([type, count]) => ({
        name: type,
        value: count
      }))
    : [];

  const dataQuality = selectedSheet && visualizationData.data_quality_metrics[selectedSheet]
    ? visualizationData.data_quality_metrics[selectedSheet]
    : null;

  const columnStats = visualizationData.column_statistics.filter(
    col => !selectedSheet || col.sheet === selectedSheet
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <FiDatabase className="w-8 h-8 text-blue-400" />
            <div>
              <h1 className="text-3xl font-bold text-white">Schema Analysis</h1>
              <p className="text-gray-400">{visualizationData.filename}</p>
            </div>
          </div>
        </div>

        {/* Sheet Selector */}
        {Object.keys(schemaData.sheets).length > 1 && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">Select Sheet:</label>
            <select
              value={selectedSheet || ''}
              onChange={(e) => setSelectedSheet(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.keys(schemaData.sheets).map((sheet) => (
                <option key={sheet} value={sheet}>{sheet}</option>
              ))}
            </select>
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <SummaryCard
            icon={<FiLayers className="w-6 h-6" />}
            title="Total Columns"
            value={currentSheet?.column_count || 0}
            color="blue"
          />
          <SummaryCard
            icon={<FiType className="w-6 h-6" />}
            title="Data Types"
            value={typeDistribution.length}
            color="green"
          />
          <SummaryCard
            icon={<FiCheckCircle className="w-6 h-6" />}
            title="Data Quality"
            value={dataQuality ? `${(dataQuality.quality_score * 100).toFixed(1)}%` : 'N/A'}
            color="purple"
          />
          <SummaryCard
            icon={<FiLink className="w-6 h-6" />}
            title="Relationships"
            value={visualizationData.relationships.length}
            color="orange"
          />
        </div>

        {/* Charts Row 1: Type Distribution & Data Quality */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Type Distribution Pie Chart */}
          <div className="bg-gray-800/50 backdrop-blur-xl rounded-lg border border-gray-700/50 p-6 shadow-xl">
            <div className="flex items-center gap-2 mb-4">
              <FiPieChart className="w-5 h-5 text-blue-400" />
              <h3 className="text-xl font-semibold text-white">Type Distribution</h3>
            </div>
            {typeDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={typeDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {typeDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400 text-center py-12">No type data available</p>
            )}
          </div>

          {/* Data Quality Metrics */}
          <div className="bg-gray-800/50 backdrop-blur-xl rounded-lg border border-gray-700/50 p-6 shadow-xl">
            <div className="flex items-center gap-2 mb-4">
              <FiTrendingUp className="w-5 h-5 text-green-400" />
              <h3 className="text-xl font-semibold text-white">Data Quality Metrics</h3>
            </div>
            {dataQuality ? (
              <div className="space-y-4">
                <QualityMetric
                  label="Completeness"
                  value={dataQuality.completeness * 100}
                  color="blue"
                />
                <QualityMetric
                  label="Quality Score"
                  value={dataQuality.quality_score * 100}
                  color="green"
                />
                <div className="pt-4 border-t border-gray-700">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-400">Total Cells</p>
                      <p className="text-white font-semibold">{dataQuality.total_cells?.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-400">Null Cells</p>
                      <p className="text-white font-semibold">{dataQuality.null_cells?.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-400">Duplicate Rows</p>
                      <p className="text-white font-semibold">{dataQuality.duplicate_rows?.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-400">Duplicate %</p>
                      <p className="text-white font-semibold">{dataQuality.duplicate_percentage?.toFixed(2)}%</p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-400 text-center py-12">No quality data available</p>
            )}
          </div>
        </div>

        {/* Column Statistics Table */}
        <div className="bg-gray-800/50 backdrop-blur-xl rounded-lg border border-gray-700/50 p-6 shadow-xl mb-6">
          <div className="flex items-center gap-2 mb-4">
            <FiBarChart2 className="w-5 h-5 text-purple-400" />
            <h3 className="text-xl font-semibold text-white">Column Statistics</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-300 font-semibold">Column</th>
                  <th className="text-left py-3 px-4 text-gray-300 font-semibold">Type</th>
                  <th className="text-left py-3 px-4 text-gray-300 font-semibold">Semantic</th>
                  <th className="text-left py-3 px-4 text-gray-300 font-semibold">Null %</th>
                  <th className="text-left py-3 px-4 text-gray-300 font-semibold">Unique %</th>
                  <th className="text-left py-3 px-4 text-gray-300 font-semibold">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {columnStats.map((col, idx) => (
                  <tr key={idx} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="py-3 px-4 text-white font-medium">{col.column}</td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-900/30 text-blue-300">
                        {col.type}
                        {col.subtype && ` (${col.subtype})`}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-300">{col.semantic_meaning}</td>
                    <td className="py-3 px-4">
                      <span className={`text-sm ${col.null_percentage > 10 ? 'text-red-400' : 'text-green-400'}`}>
                        {col.null_percentage.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-300">{col.unique_percentage.toFixed(1)}%</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-700 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              col.confidence > 0.8 ? 'bg-green-500' :
                              col.confidence > 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${col.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-400">{(col.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Relationships */}
        {visualizationData.relationships.length > 0 && (
          <div className="bg-gray-800/50 backdrop-blur-xl rounded-lg border border-gray-700/50 p-6 shadow-xl">
            <div className="flex items-center gap-2 mb-4">
              <FiLink className="w-5 h-5 text-orange-400" />
              <h3 className="text-xl font-semibold text-white">Detected Relationships</h3>
            </div>
            <div className="space-y-3">
              {visualizationData.relationships.map((rel, idx) => (
                <div
                  key={idx}
                  className="bg-gray-700/30 rounded-lg p-4 border border-gray-600/50"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-orange-900/30 text-orange-300 mr-2">
                        {rel.type}
                      </span>
                      <span className="text-white font-medium">{rel.column || rel.source_column}</span>
                      {rel.target_column && (
                        <>
                          <span className="text-gray-400 mx-2">→</span>
                          <span className="text-white">{rel.target_column}</span>
                        </>
                      )}
                    </div>
                    {rel.confidence && (
                      <span className="text-sm text-gray-400">
                        {(rel.confidence * 100).toFixed(0)}% confidence
                      </span>
                    )}
                  </div>
                  {rel.description && (
                    <p className="text-gray-400 text-sm mt-2">{rel.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const SummaryCard = ({ icon, title, value, color }) => {
  const colorClasses = {
    blue: 'bg-blue-500/20 border-blue-500/50 text-blue-400',
    green: 'bg-green-500/20 border-green-500/50 text-green-400',
    purple: 'bg-purple-500/20 border-purple-500/50 text-purple-400',
    orange: 'bg-orange-500/20 border-orange-500/50 text-orange-400',
  };

  return (
    <div className="bg-gray-800/50 backdrop-blur-xl rounded-lg border border-gray-700/50 p-6 shadow-xl">
      <div className={`inline-flex p-3 rounded-lg ${colorClasses[color]} mb-4`}>
        {icon}
      </div>
      <h3 className="text-gray-400 text-sm font-medium mb-1">{title}</h3>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
};

const QualityMetric = ({ label, value, color }) => {
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500',
    orange: 'bg-orange-500',
  };

  return (
    <div>
      <div className="flex justify-between mb-2">
        <span className="text-gray-300 text-sm">{label}</span>
        <span className="text-white font-semibold">{value.toFixed(1)}%</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-3">
        <div
          className={`h-3 rounded-full ${colorClasses[color]}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
};

export default SchemaAnalysis;

