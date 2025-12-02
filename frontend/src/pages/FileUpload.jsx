import { useState, useEffect, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { FiUpload, FiX, FiFile, FiCheckCircle, FiAlertCircle, FiLoader, FiSave, FiTrash2, FiEdit2, FiBarChart2, FiLink, FiDatabase, FiArrowRight, FiArrowDown, FiFilter, FiTrendingUp, FiTarget, FiActivity } from "react-icons/fi"
import { Button } from "@/components/ui/button"

const FileUpload = () => {
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [columns, setColumns] = useState({})
  const [definitions, setDefinitions] = useState({})
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState({ type: "", text: "" })
  const [schemaAnalysis, setSchemaAnalysis] = useState(null)
  const [loadingSchema, setLoadingSchema] = useState(false)
  const [showSchemaAnalysis, setShowSchemaAnalysis] = useState(false)
  const [expandedRelationships, setExpandedRelationships] = useState({})
  const [batchRelationships, setBatchRelationships] = useState(null)
  const [analyzingBatch, setAnalyzingBatch] = useState(false)
  const [allColumnDefinitions, setAllColumnDefinitions] = useState({})
  const [relationshipFilter, setRelationshipFilter] = useState("all") // all, cross_file, by_type, by_strength
  const [selectedType, setSelectedType] = useState("all")
  const [expandedRelationship, setExpandedRelationship] = useState(null)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  // Load existing files on mount
  useEffect(() => {
    fetchFiles()
    loadCachedRelationships()
    loadAllColumnDefinitions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchFiles = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/files/list`)
      if (response.ok) {
        const data = await response.json()
        setFiles(data.files || [])
      }
    } catch (error) {
      console.error("Error fetching files:", error)
    }
  }

  const onDrop = useCallback(async (acceptedFiles) => {
    setUploading(true)
    setMessage({ type: "", text: "" })

    // Check existing files first to prevent duplicates
    await fetchFiles()

    for (const file of acceptedFiles) {
      try {
        // Check if file with same name already exists
        const existingFile = files.find(f => f.original_filename === file.name)
        if (existingFile) {
          setMessage({ type: "warning", text: `File "${file.name}" already exists. Skipping upload.` })
          // Auto-select existing file instead
          await loadFileColumns(existingFile.file_id)
          continue
        }

        const formData = new FormData()
        formData.append("file", file)

        const response = await fetch(`${API_BASE_URL}/files/upload`, {
          method: "POST",
          body: formData,
        })

        if (response.ok) {
          const data = await response.json()
          setMessage({ type: "success", text: `File "${file.name}" uploaded successfully` })
          
          // Reload files list
          await fetchFiles()
          
          // Auto-select the newly uploaded file
          if (data.file_id) {
            await loadFileColumns(data.file_id)
          }
        } else {
          const errorData = await response.json()
          setMessage({ type: "error", text: `Error uploading "${file.name}": ${errorData.detail?.message || errorData.detail || "Unknown error"}` })
        }
      } catch (error) {
        setMessage({ type: "error", text: `Error uploading "${file.name}": ${error.message}` })
      }
    }

    setUploading(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [API_BASE_URL, files])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "text/csv": [".csv"],
    },
    multiple: true,
  })

  const loadFileColumns = async (fileId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/files/${fileId}/columns`)
      if (response.ok) {
        const data = await response.json()
        setSelectedFile(fileId)
        setColumns(data.columns || {})
        
        // Load existing definitions
        const fileInfoResponse = await fetch(`${API_BASE_URL}/files/${fileId}`)
        if (fileInfoResponse.ok) {
          const fileInfo = await fileInfoResponse.json()
          setDefinitions(fileInfo.user_definitions || {})
        }
        
        // Don't auto-load schema analysis - user will trigger it manually
      } else {
        setMessage({ type: "error", text: "Error loading file columns" })
      }
    } catch (error) {
      setMessage({ type: "error", text: `Error loading columns: ${error.message}` })
    }
  }

  const loadCachedRelationships = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/relationships/cached`)
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.relationships && data.relationships.length > 0) {
          setBatchRelationships(data)
        }
      }
    } catch (error) {
      console.error("Error loading cached relationships:", error)
    }
  }

  const loadAllColumnDefinitions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/column-definitions`)
      if (response.ok) {
        const data = await response.json()
        setAllColumnDefinitions(data.definitions || {})
      }
    } catch (error) {
      console.error("Error loading column definitions:", error)
    }
  }

  const analyzeAllRelationships = async () => {
    try {
      setAnalyzingBatch(true)
      setMessage({ type: "info", text: "Analyzing relationships across all files... This may take a moment." })
      
      const response = await fetch(`${API_BASE_URL}/relationships/analyze-all`, {
        method: "POST"
      })
      
      if (response.ok) {
        const data = await response.json()
        setBatchRelationships(data)
        setMessage({ 
          type: "success", 
          text: data.cached 
            ? `Using cached results from ${new Date(data.analyzed_at).toLocaleString()}` 
            : `Analysis complete! Found ${data.relationships?.length || 0} relationships across ${data.file_count || 0} files.` 
        })
      } else {
        const errorData = await response.json()
        setMessage({ type: "error", text: errorData.detail || "Error analyzing relationships" })
      }
    } catch (error) {
      console.error("Error analyzing relationships:", error)
      setMessage({ type: "error", text: `Error: ${error.message}` })
    } finally {
      setAnalyzingBatch(false)
    }
  }

  const handleDefinitionChange = (columnKey, value) => {
    setDefinitions((prev) => ({
      ...prev,
      [columnKey]: value,
    }))
  }

  const saveDefinitions = async () => {
    if (!selectedFile) return

    setSaving(true)
    try {
      const response = await fetch(`${API_BASE_URL}/files/${selectedFile}/definitions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(definitions),
      })

      if (response.ok) {
        setMessage({ type: "success", text: "Column definitions saved successfully" })
        await loadAllColumnDefinitions()
      } else {
        const errorData = await response.json()
        setMessage({ type: "error", text: `Error saving definitions: ${errorData.detail || "Unknown error"}` })
      }
    } catch (error) {
      setMessage({ type: "error", text: `Error saving definitions: ${error.message}` })
    } finally {
      setSaving(false)
    }
  }

  const deleteFile = async (fileId) => {
    if (!confirm("Are you sure you want to delete this file?")) return

    try {
      const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
        method: "DELETE",
      })

      if (response.ok) {
        const data = await response.json()
        setMessage({ type: "success", text: data.message || "File deleted successfully" })
        await fetchFiles()
        if (selectedFile === fileId) {
          setSelectedFile(null)
          setColumns({})
          setDefinitions({})
        }
        // Clear relationship cache display if it exists
        setBatchRelationships(null)
      } else {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
        const errorMessage = errorData.detail?.message || errorData.detail || "Error deleting file"
        setMessage({ type: "error", text: `Error deleting file: ${errorMessage}` })
      }
    } catch (error) {
      setMessage({ type: "error", text: `Error deleting file: ${error.message}` })
    }
  }

  const getFileIcon = () => {
    return <FiFile className="w-5 h-5" />
  }

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="flex gap-2 items-center mb-2 text-3xl font-bold text-gray-100">
            <FiUpload className="w-8 h-8" />
            File Upload & Column Definitions
          </h1>
          <p className="text-gray-400">
            Upload Excel/CSV files and define column meanings for master data relationship building
          </p>
        </div>

        {/* Message */}
        {message.text && (
          <div
            className={`mb-6 p-4 rounded-lg border ${
              message.type === "success"
                ? "bg-green-900/20 border-green-700/50 text-green-300"
                : message.type === "info"
                ? "bg-blue-900/20 border-blue-700/50 text-blue-300"
                : "bg-red-900/20 border-red-700/50 text-red-300"
            }`}
          >
            <div className="flex gap-2 items-start">
              {message.type === "success" ? (
                <FiCheckCircle className="h-5 w-5 mt-0.5 shrink-0" />
              ) : message.type === "info" ? (
                <FiLoader className="h-5 w-5 mt-0.5 shrink-0 animate-spin" />
              ) : (
                <FiAlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
              )}
              <span>{message.text}</span>
            </div>
          </div>
        )}

        {/* Batch Relationship Analysis Section */}
        <div className="mb-6 p-6 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-100 flex items-center gap-2">
                <FiLink className="w-5 h-5" />
                Cross-File Relationship Analysis
              </h2>
              <p className="mt-1 text-sm text-gray-400">
                Analyze relationships across all uploaded files using Gemini AI. Results are cached and updated automatically when files or definitions change.
              </p>
            </div>
            <Button
              onClick={analyzeAllRelationships}
              disabled={analyzingBatch || files.length === 0}
              className="bg-blue-600 hover:bg-blue-700 shrink-0"
            >
              {analyzingBatch ? (
                <>
                  <FiLoader className="mr-2 w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <FiBarChart2 className="mr-2 w-4 h-4" />
                  Analyze All Relationships
                </>
              )}
            </Button>
          </div>

          {batchRelationships && batchRelationships.relationships && batchRelationships.relationships.length > 0 && (
            <div className="mt-4 space-y-4">
              {/* Summary Statistics */}
              {batchRelationships.analysis_summary && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 rounded-lg bg-gray-800/50 border border-gray-700">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-400">{batchRelationships.analysis_summary.total_count}</div>
                    <div className="text-xs text-gray-400">Total Relationships</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-400">{batchRelationships.analysis_summary.cross_file_count || 0}</div>
                    <div className="text-xs text-gray-400">Cross-File</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-400">{batchRelationships.analysis_summary.gemini_count || 0}</div>
                    <div className="text-xs text-gray-400">AI Detected</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-yellow-400">
                      {batchRelationships.analysis_summary.by_strength?.strong || 0}
                    </div>
                    <div className="text-xs text-gray-400">Strong</div>
                  </div>
                </div>
              )}

              {/* Filters */}
              <div className="flex flex-wrap gap-2 items-center p-3 rounded-lg bg-gray-800/30 border border-gray-700/50">
                <FiFilter className="w-4 h-4 text-gray-400" />
                <span className="text-xs text-gray-400">Filter:</span>
                <button
                  onClick={() => { setRelationshipFilter("all"); setSelectedType("all"); }}
                  className={`px-3 py-1 text-xs rounded transition-colors ${
                    relationshipFilter === "all" ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setRelationshipFilter("cross_file")}
                  className={`px-3 py-1 text-xs rounded transition-colors ${
                    relationshipFilter === "cross_file" ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }`}
                >
                  Cross-File Only
                </button>
                {batchRelationships.analysis_summary?.by_type && (
                  Object.entries(batchRelationships.analysis_summary.by_type).map(([type, count]) => (
                    <button
                      key={type}
                      onClick={() => { setRelationshipFilter("by_type"); setSelectedType(type); }}
                      className={`px-3 py-1 text-xs rounded transition-colors ${
                        relationshipFilter === "by_type" && selectedType === type ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                      }`}
                    >
                      {type.replace(/_/g, " ")} ({count})
                    </button>
                  ))
                )}
              </div>

              {/* Relationships List */}
              <div className="max-h-96 overflow-y-auto space-y-2 p-4 rounded-lg bg-gray-800/50 border border-gray-700">
                {(() => {
                  let filtered = batchRelationships.relationships;
                  
                  if (relationshipFilter === "cross_file") {
                    filtered = filtered.filter(rel => {
                      const source = rel.source_column || rel.column || "";
                      const target = rel.target_column || "";
                      const sourceFile = source.split("::")[0];
                      const targetFile = target.split("::")[0];
                      return sourceFile && targetFile && sourceFile !== targetFile;
                    });
                  } else if (relationshipFilter === "by_type" && selectedType !== "all") {
                    filtered = filtered.filter(rel => rel.type === selectedType);
                  }
                  
                  // Sort by confidence and impact
                  filtered = filtered.sort((a, b) => {
                    const impactOrder = { critical: 3, important: 2, informational: 1 };
                    const aImpact = impactOrder[a.impact] || 1;
                    const bImpact = impactOrder[b.impact] || 1;
                    if (aImpact !== bImpact) return bImpact - aImpact;
                    return (b.confidence || 0) - (a.confidence || 0);
                  });
                  
                  return filtered.map((rel, idx) => {
                    const source = rel.source_column || rel.column || "";
                    const target = rel.target_column || "";
                    const sourceParts = source.split("::");
                    const targetParts = target.split("::");
                    const sourceFile = sourceParts[0] || "";
                    const sourceCol = sourceParts[2] || sourceParts[0] || source;
                    const targetFile = targetParts[0] || "";
                    const targetCol = targetParts[2] || targetParts[0] || target;
                    const isCrossFile = sourceFile && targetFile && sourceFile !== targetFile;
                    const isExpanded = expandedRelationship === idx;
                    
                    return (
                      <div key={idx} className="p-4 rounded-lg bg-gray-900/50 border border-gray-700/50 hover:border-gray-600 transition-colors">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2 flex-wrap">
                              <span className={`px-2 py-1 text-xs font-medium rounded ${
                                rel.type === "foreign_key" ? "bg-blue-900/50 text-blue-300" :
                                rel.type === "calculated" ? "bg-green-900/50 text-green-300" :
                                rel.type === "temporal" ? "bg-purple-900/50 text-purple-300" :
                                rel.type === "hierarchical" ? "bg-yellow-900/50 text-yellow-300" :
                                rel.type === "cross_file_flow" ? "bg-red-900/50 text-red-300" :
                                "bg-gray-700 text-gray-300"
                              }`}>
                                {rel.type?.replace(/_/g, " ") || "unknown"}
                              </span>
                              {rel.strength && (
                                <span className={`px-2 py-1 text-xs rounded ${
                                  rel.strength === "strong" ? "bg-green-900/30 text-green-400" :
                                  rel.strength === "medium" ? "bg-yellow-900/30 text-yellow-400" :
                                  "bg-gray-700 text-gray-400"
                                }`}>
                                  {rel.strength}
                                </span>
                              )}
                              {rel.impact && (
                                <span className={`px-2 py-1 text-xs rounded ${
                                  rel.impact === "critical" ? "bg-red-900/30 text-red-400" :
                                  rel.impact === "important" ? "bg-orange-900/30 text-orange-400" :
                                  "bg-gray-700 text-gray-400"
                                }`}>
                                  {rel.impact}
                                </span>
                              )}
                              {isCrossFile && (
                                <span className="px-2 py-1 text-xs rounded bg-indigo-900/30 text-indigo-400">
                                  Cross-File
                                </span>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-sm font-medium text-gray-200">{sourceCol}</span>
                              <FiArrowRight className="w-4 h-4 text-gray-500" />
                              <span className="text-sm font-medium text-gray-200">{targetCol}</span>
                            </div>
                            
                            {isCrossFile && (
                              <div className="text-xs text-gray-500 mb-2">
                                <span className="font-medium">{sourceFile}</span> → <span className="font-medium">{targetFile}</span>
                              </div>
                            )}
                            
                            {rel.description && (
                              <p className="text-sm text-gray-400 mb-2">{rel.description}</p>
                            )}
                            
                            {isExpanded && (
                              <div className="mt-3 pt-3 border-t border-gray-700 space-y-2">
                                {rel.evidence && (
                                  <div>
                                    <span className="text-xs font-medium text-gray-500">Evidence: </span>
                                    <span className="text-xs text-gray-400">{rel.evidence}</span>
                                  </div>
                                )}
                                {rel.formula && (
                                  <div>
                                    <span className="text-xs font-medium text-gray-500">Formula: </span>
                                    <span className="text-xs text-gray-400 font-mono">{rel.formula}</span>
                                  </div>
                                )}
                                {rel.business_meaning && (
                                  <div>
                                    <span className="text-xs font-medium text-gray-500">Business Meaning: </span>
                                    <span className="text-xs text-gray-400">{rel.business_meaning}</span>
                                  </div>
                                )}
                                {rel.cardinality && (
                                  <div>
                                    <span className="text-xs font-medium text-gray-500">Cardinality: </span>
                                    <span className="text-xs text-gray-400">{rel.cardinality}</span>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                          
                          <div className="flex flex-col items-end gap-2 ml-4">
                            {rel.confidence !== undefined && (
                              <div className="text-right">
                                <div className="text-sm font-bold text-gray-300">{(rel.confidence * 100).toFixed(0)}%</div>
                                <div className="text-xs text-gray-500">confidence</div>
                              </div>
                            )}
                            <button
                              onClick={() => setExpandedRelationship(isExpanded ? null : idx)}
                              className="text-xs text-blue-400 hover:text-blue-300"
                            >
                              {isExpanded ? "Less" : "More"}
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  });
                })()}
                
                {batchRelationships.relationships.length === 0 && (
                  <p className="text-center text-gray-500 py-8">No relationships found</p>
                )}
              </div>
              
              {batchRelationships.cached && batchRelationships.analyzed_at && (
                <p className="text-xs text-center text-gray-500">
                  Cached results from {new Date(batchRelationships.analyzed_at).toLocaleString()}
                </p>
              )}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left Column: File Upload & List */}
          <div className="space-y-6 lg:col-span-1">
            {/* Upload Area */}
            <div className="p-6 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50">
              <h2 className="mb-4 text-xl font-semibold text-gray-100">Upload Files</h2>
              
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActive
                    ? "border-blue-500 bg-blue-900/20"
                    : "border-gray-700 hover:border-gray-600 bg-gray-800/30"
                }`}
              >
                <input {...getInputProps()} />
                {uploading ? (
                  <div className="flex flex-col gap-2 items-center">
                    <FiLoader className="w-8 h-8 text-blue-400 animate-spin" />
                    <p className="text-gray-400">Uploading...</p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2 items-center">
                    <FiUpload className="w-8 h-8 text-gray-400" />
                    <p className="text-gray-300">
                      {isDragActive ? "Drop files here" : "Drag & drop files here"}
                    </p>
                    <p className="text-sm text-gray-500">or click to select</p>
                    <p className="mt-2 text-xs text-gray-600">Supports: .xlsx, .xls, .csv</p>
                  </div>
                )}
              </div>
            </div>

            {/* Files List */}
            <div className="p-6 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50">
              <h2 className="mb-4 text-xl font-semibold text-gray-100">Uploaded Files</h2>
              
              {files.length === 0 ? (
                <p className="py-8 text-center text-gray-400">No files uploaded yet</p>
              ) : (
                <div className="space-y-2">
                  {files.map((file) => (
                    <div
                      key={file.file_id}
                      className={`p-3 rounded-lg border transition-colors ${
                        selectedFile === file.file_id
                          ? "bg-blue-900/20 border-blue-700/50"
                          : "bg-gray-800/50 border-gray-700/50"
                      }`}
                    >
                      <div 
                        className="cursor-pointer"
                        onClick={() => loadFileColumns(file.file_id)}
                      >
                        <div className="flex justify-between items-center">
                          <div className="flex flex-1 gap-2 items-center min-w-0">
                            {getFileIcon(file.file_type)}
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-200 truncate">
                                {file.filename}
                              </p>
                              <p className="text-xs text-gray-500">
                                {file.file_type?.toUpperCase()} • {file.sheet_names?.length || 0} sheet(s)
                              </p>
                            </div>
                          </div>
                          <div className="flex gap-2 items-center" onClick={(e) => e.stopPropagation()}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                deleteFile(file.file_id)
                              }}
                              className="p-1 text-gray-400 transition-colors hover:text-red-400"
                              title="Delete file"
                            >
                              <FiTrash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Columns & Definitions & Schema Analysis */}
          <div className="space-y-6 lg:col-span-2">
            {selectedFile ? (
              <>
                {/* Schema Analysis Section */}
                {showSchemaAnalysis && schemaAnalysis && (
                  <div className="p-6 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50">
                    <div className="flex justify-between items-center mb-6">
                      <div className="flex gap-2 items-center">
                        <FiDatabase className="w-5 h-5 text-blue-400" />
                        <h2 className="text-xl font-semibold text-gray-100">Schema Analysis & Relationships</h2>
                      </div>
                      <button
                        onClick={() => setShowSchemaAnalysis(false)}
                        className="text-gray-400 hover:text-gray-200"
                      >
                        <FiX className="w-5 h-5" />
                      </button>
                    </div>

                    {loadingSchema ? (
                      <div className="flex justify-center items-center py-12">
                        <FiLoader className="w-8 h-8 text-blue-400 animate-spin" />
                        <span className="ml-3 text-gray-400">Analyzing schema...</span>
                      </div>
                    ) : schemaAnalysis?.visualization ? (
                      <div className="space-y-6">
                        {/* Relationship Type Guide */}
                        <div className="p-4 rounded-lg border bg-blue-900/20 border-blue-800/50">
                          <h4 className="mb-3 text-sm font-semibold text-blue-200">Understanding Relationship Types:</h4>
                          <div className="grid grid-cols-1 gap-3 text-xs text-blue-300 md:grid-cols-2">
                            <div><strong>Foreign Key:</strong> Column references another column (e.g., Product_ID → Product_Name)</div>
                            <div><strong>Hierarchical:</strong> Parent-child relationship (e.g., Line → Machine → Station)</div>
                            <div><strong>Temporal:</strong> Time-based relationship (e.g., Start_Date → End_Date)</div>
                            <div><strong>Categorical:</strong> Status/enum relationship (e.g., Status → Status_Code)</div>
                            <div><strong>Calculated:</strong> Derived/computed relationship (e.g., Opening + Received - Consumption = Closing)</div>
                            <div><strong>Semantic:</strong> Related concepts (e.g., Product → Supplier, Date → Batch_ID)</div>
                          </div>
                        </div>

                        {/* Column Relationships Matrix - Expandable Cards View */}
                        <div className="p-4 rounded-lg border bg-gray-800/50 border-gray-700/50">
                          <h3 className="flex gap-2 items-center mb-4 text-lg font-semibold text-gray-200">
                            <FiLink className="w-5 h-5 text-blue-400" />
                            Column Relationships Matrix
                          </h3>
                          <p className="mb-4 text-sm text-gray-400">
                            Expandable view showing each column and its relationships. Click on a column to see all its connections.
                          </p>
                          
                          {/* Column Relationship Cards */}
                          {schemaAnalysis.visualization.column_statistics && (
                            <div className="space-y-4">
                              {schemaAnalysis.visualization.column_statistics.map((col, colIdx) => {
                                const colRelationships = schemaAnalysis.visualization.relationships.filter(
                                  rel => rel.source_column === col.column || rel.target_column === col.column
                                )
                                
                                if (colRelationships.length === 0) return null
                                
                                const isExpanded = expandedRelationships[col.column] || false
                                
                                return (
                                  <div key={colIdx} className="overflow-hidden rounded-lg border bg-gray-900/50 border-gray-700/50">
                                    {/* Column Header */}
                                    <button
                                      onClick={() => setExpandedRelationships(prev => ({
                                        ...prev,
                                        [col.column]: !prev[col.column]
                                      }))}
                                      className="flex justify-between items-center p-4 w-full transition-colors hover:bg-gray-800/50"
                                    >
                                      <div className="flex flex-1 gap-3 items-center text-left">
                                        <div className={`w-3 h-3 rounded-full ${
                                          col.type === 'id' ? 'bg-blue-500' :
                                          col.type === 'date' ? 'bg-green-500' :
                                          col.type === 'numeric' ? 'bg-yellow-500' :
                                          col.type === 'categorical' ? 'bg-purple-500' :
                                          col.type === 'text' ? 'bg-pink-500' :
                                          col.type === 'boolean' ? 'bg-cyan-500' : 'bg-gray-500'
                                        }`}></div>
                                        <div>
                                          <div className="font-semibold text-white">{col.column}</div>
                                          <div className="text-xs text-gray-400">
                                            {col.type} • {col.semantic_meaning || 'N/A'} • {colRelationships.length} relationship{colRelationships.length !== 1 ? 's' : ''}
                                          </div>
                                        </div>
                                      </div>
                                      <div className="flex gap-4 items-center">
                                        <span className="text-sm text-gray-400">{colRelationships.length} connections</span>
                                        {isExpanded ? <FiArrowDown className="w-5 h-5 text-gray-400" /> : <FiArrowRight className="w-5 h-5 text-gray-400" />}
                                      </div>
                                    </button>
                                    
                                    {/* Expanded Relationships */}
                                    {isExpanded && (
                                      <div className="p-4 space-y-3 border-t border-gray-700/50">
                                        {colRelationships.map((rel, relIdx) => {
                                          const otherCol = rel.source_column === col.column ? rel.target_column : rel.source_column
                                          const typeColors = {
                                            'foreign_key': 'bg-blue-900/30 text-blue-300 border-blue-700/50',
                                            'hierarchical': 'bg-green-900/30 text-green-300 border-green-700/50',
                                            'temporal': 'bg-yellow-900/30 text-yellow-300 border-yellow-700/50',
                                            'categorical': 'bg-purple-900/30 text-purple-300 border-purple-700/50',
                                            'calculated': 'bg-pink-900/30 text-pink-300 border-pink-700/50',
                                            'semantic': 'bg-cyan-900/30 text-cyan-300 border-cyan-700/50'
                                          }
                                          const typeColor = typeColors[rel.type] || 'bg-gray-900/30 text-gray-300 border-gray-700/50'
                                          
                                          return (
                                            <div key={relIdx} className="p-3 rounded-lg border bg-gray-800/30 border-gray-700/30">
                                              <div className="flex gap-3 items-start">
                                                <div className="flex-1">
                                                  <div className="flex flex-wrap gap-2 items-center mb-2">
                                                    <span className={`px-2 py-1 text-xs font-semibold rounded border ${typeColor}`}>
                                                      {rel.type?.replace('_', ' ').toUpperCase()}
                                                    </span>
                                                    <span className="font-medium text-white">{col.column}</span>
                                                    <FiArrowRight className="w-4 h-4 text-gray-500" />
                                                    <span className="font-medium text-white">{otherCol}</span>
                                                  </div>
                                                  {rel.description && (
                                                    <p className="mb-1 text-sm text-gray-300">{rel.description}</p>
                                                  )}
                                                  {rel.evidence && (
                                                    <p className="text-xs italic text-gray-500">Evidence: {rel.evidence}</p>
                                                  )}
                                                </div>
                                                <div className="text-right shrink-0">
                                                  <div className="mb-1 text-xs text-gray-400">Confidence</div>
                                                  <div className="flex gap-2 items-center">
                                                    <div className="w-16 h-2 bg-gray-700 rounded-full">
                                                      <div
                                                        className={`h-2 rounded-full ${
                                                          (rel.confidence || 0) > 0.8 ? 'bg-green-500' :
                                                          (rel.confidence || 0) > 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                                                        }`}
                                                        style={{ width: `${(rel.confidence || 0) * 100}%` }}
                                                      />
                                                    </div>
                                                    <span className={`text-sm font-semibold ${
                                                      (rel.confidence || 0) > 0.8 ? 'text-green-400' :
                                                      (rel.confidence || 0) > 0.5 ? 'text-yellow-400' : 'text-red-400'
                                                    }`}>
                                                      {(rel.confidence * 100).toFixed(0)}%
                                                    </span>
                                                  </div>
                                                </div>
                                              </div>
                                            </div>
                                          )
                                        })}
                                      </div>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>

                        {/* Detailed Relationships List - All relationships in one place */}
                        {schemaAnalysis.visualization.relationships?.length > 0 && (
                          <div className="p-4 rounded-lg border bg-gray-800/50 border-gray-700/50">
                            <h3 className="mb-4 text-lg font-semibold text-gray-200">All Relationships Summary</h3>
                            <div className="p-3 mb-4 rounded-lg border bg-blue-900/20 border-blue-800/50">
                              <p className="text-sm text-blue-200">
                                <strong>Total Relationships Found:</strong> {schemaAnalysis.visualization.relationships.length}
                              </p>
                              <p className="mt-1 text-xs text-blue-300">
                                Complete list of all detected relationships between columns. Use the matrix above to explore relationships by column.
                              </p>
                            </div>
                            <div className="overflow-y-auto space-y-3 max-h-96">
                              {schemaAnalysis.visualization.relationships.map((rel, idx) => {
                                const typeColors = {
                                  'foreign_key': 'bg-blue-900/30 text-blue-300 border-blue-700/50',
                                  'hierarchical': 'bg-green-900/30 text-green-300 border-green-700/50',
                                  'temporal': 'bg-yellow-900/30 text-yellow-300 border-yellow-700/50',
                                  'categorical': 'bg-purple-900/30 text-purple-300 border-purple-700/50',
                                  'calculated': 'bg-pink-900/30 text-pink-300 border-pink-700/50',
                                  'semantic': 'bg-cyan-900/30 text-cyan-300 border-cyan-700/50'
                                }
                                const typeColor = typeColors[rel.type] || 'bg-gray-900/30 text-gray-300 border-gray-700/50'
                                
                                return (
                                  <div key={idx} className="p-4 rounded-lg border transition-colors bg-gray-900/50 border-gray-700/30 hover:border-gray-600">
                                    <div className="flex gap-4 justify-between items-start">
                                      <div className="flex-1">
                                        <div className="flex flex-wrap gap-2 items-center mb-2">
                                          <span className={`px-3 py-1 text-xs font-semibold rounded border ${typeColor}`}>
                                            {rel.type?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
                                          </span>
                                          <div className="flex gap-2 items-center">
                                            <span className="text-base font-semibold text-white">{rel.source_column || rel.column}</span>
                                            {rel.target_column && (
                                              <>
                                                <span className="text-lg text-gray-500">→</span>
                                                <span className="text-base font-semibold text-white">{rel.target_column}</span>
                                              </>
                                            )}
                                          </div>
                                        </div>
                                        
                                        {rel.description && (
                                          <div className="p-2 mt-2 rounded border-l-2 border-blue-500 bg-gray-800/50">
                                            <p className="text-sm leading-relaxed text-gray-300">{rel.description}</p>
                                          </div>
                                        )}
                                        
                                        {rel.evidence && (
                                          <div className="p-2 mt-2 rounded bg-gray-800/30">
                                            <p className="text-xs text-gray-400">
                                              <strong className="text-gray-500">Evidence:</strong> {rel.evidence}
                                            </p>
                                          </div>
                                        )}
                                        
                                        {rel.direction && rel.direction !== 'source_to_target' && (
                                          <div className="mt-2">
                                            <span className="px-2 py-1 text-xs text-purple-300 rounded bg-purple-900/30">
                                              {rel.direction === 'bidirectional' ? '↔ Bidirectional' : 'Direction: ' + rel.direction}
                                            </span>
                                          </div>
                                        )}
                                      </div>
                                      
                                      <div className="flex flex-col gap-2 items-end shrink-0">
                                        <div className="text-right">
                                          <div className="mb-1 text-xs text-gray-500">Confidence</div>
                                          <div className="flex gap-2 items-center">
                                            <div className="w-20 h-2 bg-gray-700 rounded-full">
                                              <div
                                                className={`h-2 rounded-full ${
                                                  (rel.confidence || 0) > 0.8 ? 'bg-green-500' :
                                                  (rel.confidence || 0) > 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                                                }`}
                                                style={{ width: `${(rel.confidence || 0) * 100}%` }}
                                              />
                                            </div>
                                            <span className={`text-sm font-semibold ${
                                              (rel.confidence || 0) > 0.8 ? 'text-green-400' :
                                              (rel.confidence || 0) > 0.5 ? 'text-yellow-400' : 'text-red-400'
                                            }`}>
                                              {(rel.confidence * 100).toFixed(0)}%
                                            </span>
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="py-8 text-center text-gray-400">No schema analysis available</p>
                    )}
                  </div>
                )}

                {/* Column Definitions Section */}
                <div className="p-6 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50">
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-semibold text-gray-100">Column Definitions</h2>
                    <div className="flex gap-2 items-center">
                      <Button
                        onClick={saveDefinitions}
                        disabled={saving}
                        className="shrink-0"
                      >
                        {saving ? (
                          <>
                            <FiLoader className="mr-2 w-4 h-4 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <FiSave className="mr-2 w-4 h-4" />
                            Save Definitions
                          </>
                        )}
                      </Button>
                    </div>
                  </div>

                {Object.keys(columns).length === 0 ? (
                  <p className="py-8 text-center text-gray-400">No columns found</p>
                ) : (
                  <div className="space-y-6">
                    {Object.entries(columns).map(([sheetName, sheetColumns]) => (
                      <div key={sheetName} className="pb-6 border-b border-gray-700/50 last:border-b-0 last:pb-0">
                        <h3 className="flex gap-2 items-center mb-4 text-lg font-semibold text-gray-200">
                          <FiFile className="w-5 h-5" />
                          {sheetName}
                          <span className="text-sm font-normal text-gray-500">
                            ({sheetColumns.length} columns)
                          </span>
                        </h3>

                        <div className="space-y-4">
                          {sheetColumns.map((column) => {
                            const columnKey = `${sheetName}::${column.name}`
                            return (
                              <div
                                key={columnKey}
                                className="p-4 rounded-lg border bg-gray-800/50 border-gray-700/50"
                              >
                                <div className="flex justify-between items-start mb-2">
                                  <div className="flex-1">
                                    <div className="flex gap-2 items-center mb-1">
                                      <span className="font-medium text-gray-200">{column.name}</span>
                                      <span className="text-xs px-2 py-0.5 bg-gray-700/50 rounded text-gray-400">
                                        {column.type}
                                      </span>
                                      {column.null_count > 0 && (
                                        <span className="text-xs text-yellow-400">
                                          {column.null_count} nulls
                                        </span>
                                      )}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                      Unique: {column.unique_count} • Nulls: {column.null_count}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="mt-3">
                                  <label className="block mb-2 text-sm font-medium text-gray-300">
                                    User Definition (for master data relationship building)
                                  </label>
                                  <textarea
                                    value={definitions[columnKey] || ""}
                                    onChange={(e) => handleDefinitionChange(columnKey, e.target.value)}
                                    placeholder="Enter definition/description for this column (e.g., 'Product ID - Unique identifier for products', 'Customer Name - Full name of customer')"
                                    className="px-4 py-2 w-full placeholder-gray-600 text-gray-100 rounded-lg border border-gray-700 resize-none bg-gray-900/50 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                                    rows={3}
                                  />
                                  {column.user_definition && (
                                    <p className="mt-1 text-xs italic text-gray-500">
                                      Previously saved: {column.user_definition}
                                    </p>
                                  )}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                </div>
              </>
            ) : (
              <div className="p-6 rounded-lg border shadow-lg backdrop-blur-xl bg-gray-900/80 border-gray-800/50">
                <div className="py-12 text-center">
                  <FiFile className="mx-auto mb-4 w-12 h-12 text-gray-600" />
                  <p className="text-gray-400">Select a file to view and define columns</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default FileUpload

