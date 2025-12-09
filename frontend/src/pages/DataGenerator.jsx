import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { FiPlay, FiRefreshCw, FiFileText, FiCheckCircle, FiAlertCircle, FiLoader, FiDatabase, FiInfo, FiPlus, FiX } from "react-icons/fi"
import { useAuth } from "@/contexts/AuthContext"

const DataGenerator = () => {
  const { user, token } = useAuth()
  const [isGenerating, setIsGenerating] = useState(false)
  const [status, setStatus] = useState(null) // 'success', 'error', null
  const [message, setMessage] = useState("")
  const [generatedFiles, setGeneratedFiles] = useState([])
  const [existingFiles, setExistingFiles] = useState([])
  const [schemaPreview, setSchemaPreview] = useState(null)
  const [rowsPerFile, setRowsPerFile] = useState({})
  const [addToExisting, setAddToExisting] = useState(false)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [loading, setLoading] = useState(true)
  const [rowsForExistingSheets, setRowsForExistingSheets] = useState({}) // {file_id: {sheet_name: num_rows}}
  const [showExistingSheets, setShowExistingSheets] = useState(false)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  useEffect(() => {
    if (user && token) {
      loadSchemaPreview()
      loadExistingFiles()
    }
  }, [user, token])

  const loadSchemaPreview = async (useAI = true) => {
    try {
      const response = await fetch(`${API_BASE_URL}/data-generator/schema-preview?use_ai=${useAI}`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setSchemaPreview(data)
          // Initialize rows per file with default 100
          const initialRows = {}
          data.schema_templates.forEach(template => {
            initialRows[template.name] = 100
          })
          setRowsPerFile(initialRows)
        }
      }
    } catch (error) {
      console.error("Error loading schema preview:", error)
    } finally {
      setLoading(false)
    }
  }

  const loadExistingFiles = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/data-generator/existing-files`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setExistingFiles(data.files || [])
        }
      }
    } catch (error) {
      console.error("Error loading existing files:", error)
    }
  }

  const handleGenerate = async () => {
    if (!schemaPreview || !schemaPreview.schema_templates || schemaPreview.schema_templates.length === 0) {
      setStatus("error")
      setMessage("No schema templates available for your industry")
      return
    }

    // Check if user has existing files
    if (existingFiles.length > 0 && !addToExisting) {
      setShowConfirmDialog(true)
      return
    }

    await generateData()
  }

  const generateData = async () => {
    setIsGenerating(true)
    setStatus(null)
    setMessage("")
    setShowConfirmDialog(false)

    try {
      const payload = {
        rows_per_file: rowsPerFile,
        add_to_existing: addToExisting
      }
      
      // Add existing sheets generation if configured
      const hasExistingSheets = Object.keys(rowsForExistingSheets).length > 0
      if (hasExistingSheets) {
        payload.generate_for_existing_sheets = rowsForExistingSheets
      }

      const response = await fetch(`${API_BASE_URL}/data-generator/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      const data = await response.json()

      if (data.success) {
        setStatus("success")
        const existingCount = hasExistingSheets ? Object.values(rowsForExistingSheets).reduce((sum, sheets) => sum + Object.keys(sheets).length, 0) : 0
        const newCount = data.total_files - existingCount
        setMessage(`Successfully generated ${data.total_files} file(s) with ${data.total_rows} total rows${existingCount > 0 ? ` (${existingCount} existing sheets updated)` : ''}`)
        setGeneratedFiles(data.generated_files || [])
        await loadExistingFiles() // Refresh existing files
        setRowsForExistingSheets({}) // Reset
      } else {
        setStatus("error")
        setMessage(data.error || "Data generation failed")
      }
    } catch (error) {
      setStatus("error")
      setMessage(`Error: ${error.message}`)
    } finally {
      setIsGenerating(false)
    }
  }
  
  const handleExistingSheetRowsChange = (fileId, sheetName, value) => {
    setRowsForExistingSheets(prev => {
      const newState = { ...prev }
      if (!newState[fileId]) {
        newState[fileId] = {}
      }
      if (parseInt(value) > 0) {
        newState[fileId][sheetName] = parseInt(value) || 0
      } else {
        delete newState[fileId][sheetName]
        if (Object.keys(newState[fileId]).length === 0) {
          delete newState[fileId]
        }
      }
      return newState
    })
  }

  const handleRowsChange = (fileName, value) => {
    setRowsPerFile(prev => ({
      ...prev,
      [fileName]: parseInt(value) || 0
    }))
  }

  if (loading) {
    return (
      <div className="p-4 md:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <FiLoader className="h-8 w-8 text-gray-400 animate-spin" />
            <span className="ml-3 text-gray-400">Loading schema preview...</span>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="p-4 md:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-yellow-900/20 border border-yellow-800/50 rounded-lg p-6">
            <div className="flex items-start gap-3">
              <FiAlertCircle className="h-5 w-5 text-yellow-400 mt-0.5 shrink-0" />
              <div>
                <h3 className="text-lg font-semibold text-yellow-300 mb-2">Authentication Required</h3>
                <p className="text-yellow-200/80">Please log in to generate data.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-100 mb-2 flex items-center gap-2">
            <FiDatabase className="h-8 w-8" />
            Data Generator
          </h1>
          <p className="text-gray-400">
            Generate realistic data for your industry ({schemaPreview?.industry?.display_name || user.industry}) using AI
          </p>
        </div>

        {/* Industry Info */}
        {schemaPreview && schemaPreview.industry && (
          <div className="mb-6 bg-blue-900/20 border border-blue-800/50 rounded-lg p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3 flex-1">
                <span className="text-2xl">{schemaPreview.industry.icon}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-lg font-semibold text-blue-300">{schemaPreview.industry.display_name}</h3>
                    {schemaPreview.is_dynamic && (
                      <span className="px-2 py-0.5 bg-green-900/30 border border-green-700/50 text-green-300 text-xs rounded">
                        AI-Enhanced
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-blue-200/80">{schemaPreview.industry.description}</p>
                </div>
              </div>
              <button
                onClick={() => loadSchemaPreview(!schemaPreview.is_dynamic)}
                className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
                title={schemaPreview.is_dynamic ? "Use static templates" : "Use AI-enhanced templates"}
              >
                <FiRefreshCw className="h-4 w-4" />
                {schemaPreview.is_dynamic ? "Static" : "AI"}
              </button>
            </div>
          </div>
        )}

        {/* Schema Preview */}
        {schemaPreview && schemaPreview.schema_templates && schemaPreview.schema_templates.length > 0 && (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mb-6">
            <h2 className="text-xl font-semibold text-gray-100 mb-4 flex items-center gap-2">
              <FiFileText className="h-5 w-5" />
              Files & Columns Preview
            </h2>
            <p className="text-sm text-gray-400 mb-4">
              Review the files and columns that will be generated. Adjust the number of rows for each file.
            </p>
            
            <div className="space-y-4">
              {schemaPreview.schema_templates.map((template, idx) => (
                <div key={idx} className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-100 mb-1">{template.name}</h3>
                      {template.description && (
                        <p className="text-sm text-gray-400 mb-2">{template.description}</p>
                      )}
                      <div className="flex flex-wrap gap-2 mt-2">
                        {template.columns.map((col, colIdx) => (
                          <span
                            key={colIdx}
                            className="px-2 py-1 bg-gray-700/50 text-gray-300 text-xs rounded border border-gray-600"
                          >
                            {col}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="ml-4">
                      <label className="block text-sm font-medium text-gray-300 mb-2 text-right">
                        Rows
                      </label>
                      <input
                        type="number"
                        value={rowsPerFile[template.name] || 0}
                        onChange={(e) => handleRowsChange(template.name, e.target.value)}
                        className="w-24 px-3 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-600"
                        min="0"
                        disabled={isGenerating}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Existing Files */}
        {existingFiles.length > 0 && (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-100 flex items-center gap-2">
                <FiFileText className="h-5 w-5" />
                Existing Files ({existingFiles.length})
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowExistingSheets(!showExistingSheets)}
                  className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
                  disabled={isGenerating}
                >
                  {showExistingSheets ? "Hide" : "Show"} Sheets & Columns
                </button>
                <button
                  onClick={loadExistingFiles}
                  className="text-gray-400 hover:text-gray-100 transition-colors"
                  disabled={isGenerating}
                >
                  <FiRefreshCw className="h-5 w-5" />
                </button>
              </div>
            </div>
            
            {showExistingSheets && (
              <div className="mb-4 space-y-4">
                {existingFiles.map((file, idx) => (
                  <div key={idx} className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <span className="text-gray-300 font-medium">{file.original_filename}</span>
                        <span className="text-gray-400 text-sm ml-2">
                          ({file.sheet_count || 0} sheet(s), {file.row_count || 0} total rows)
                        </span>
                      </div>
                    </div>
                    
                    {file.sheets && file.sheets.length > 0 && (
                      <div className="space-y-3">
                        {file.sheets.map((sheet, sheetIdx) => (
                          <div key={sheetIdx} className="bg-gray-900/50 border border-gray-600/50 rounded-lg p-3">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className="text-gray-200 font-medium">{sheet.name}</span>
                                <span className="text-gray-400 text-xs">
                                  {sheet.row_count} rows, {sheet.columns.length} columns
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <label className="text-xs text-gray-400">Add rows:</label>
                                <input
                                  type="number"
                                  value={rowsForExistingSheets[file.file_id]?.[sheet.name] || 0}
                                  onChange={(e) => handleExistingSheetRowsChange(file.file_id, sheet.name, e.target.value)}
                                  className="w-20 px-2 py-1 bg-gray-800/50 border border-gray-700 rounded text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                                  min="0"
                                  disabled={isGenerating}
                                  placeholder="0"
                                />
                              </div>
                            </div>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {sheet.columns.slice(0, 10).map((col, colIdx) => (
                                <span
                                  key={colIdx}
                                  className="px-2 py-0.5 bg-gray-700/50 text-gray-300 text-xs rounded border border-gray-600"
                                >
                                  {col}
                                </span>
                              ))}
                              {sheet.columns.length > 10 && (
                                <span className="px-2 py-0.5 text-gray-500 text-xs">
                                  +{sheet.columns.length - 10} more
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {!showExistingSheets && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                {existingFiles.map((file, idx) => (
                  <div
                    key={idx}
                    className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-gray-300 font-medium">{file.original_filename}</span>
                      <span className="text-gray-400 text-sm">
                        {file.row_count || 0} rows
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Uploaded: {new Date(file.uploaded_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="flex items-center gap-2 mt-4">
              <input
                type="checkbox"
                id="add-to-existing"
                checked={addToExisting}
                onChange={(e) => setAddToExisting(e.target.checked)}
                className="w-4 h-4 rounded border-gray-700 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-600"
                disabled={isGenerating}
              />
              <label htmlFor="add-to-existing" className="text-sm text-gray-300 cursor-pointer">
                Add to existing files (append new rows to existing files)
              </label>
            </div>
          </div>
        )}

        {/* Generate Button */}
        <div className="mb-6">
          <Button
            onClick={handleGenerate}
            disabled={isGenerating || !schemaPreview || schemaPreview.schema_templates?.length === 0}
            className="w-full md:w-auto bg-blue-600 hover:bg-blue-700"
          >
            {isGenerating ? (
              <>
                <FiLoader className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <FiPlay className="h-4 w-4 mr-2" />
                Generate Data
              </>
            )}
          </Button>
        </div>

        {/* Confirmation Dialog */}
        {showConfirmDialog && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-md mx-4">
              <div className="flex items-start gap-3 mb-4">
                <FiInfo className="h-6 w-6 text-blue-400 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-100 mb-2">Existing Files Found</h3>
                  <p className="text-gray-300 mb-4">
                    You have {existingFiles.length} existing file(s). Would you like to add new data to these files, or generate new files?
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <Button
                  onClick={() => {
                    setAddToExisting(true)
                    generateData()
                  }}
                  className="flex-1 bg-blue-600 hover:bg-blue-700"
                >
                  <FiPlus className="h-4 w-4 mr-2" />
                  Add to Existing
                </Button>
                <Button
                  onClick={() => {
                    setAddToExisting(false)
                    generateData()
                  }}
                  className="flex-1 bg-gray-700 hover:bg-gray-600"
                >
                  Generate New Files
                </Button>
                <Button
                  onClick={() => setShowConfirmDialog(false)}
                  className="bg-gray-700 hover:bg-gray-600"
                >
                  <FiX className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Status Message */}
        {status && (
          <div
            className={`mb-6 p-4 rounded-lg border ${
              status === "success"
                ? "bg-green-900/20 border-green-700/50 text-green-300"
                : "bg-red-900/20 border-red-700/50 text-red-300"
            }`}
          >
            <div className="flex items-start gap-2">
              {status === "success" ? (
                <FiCheckCircle className="h-5 w-5 mt-0.5 shrink-0" />
              ) : (
                <FiAlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
              )}
              <div className="flex-1">
                <span className="font-medium">{message}</span>
              </div>
            </div>
          </div>
        )}

        {/* Generated Files */}
        {status === "success" && generatedFiles.length > 0 && (
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mb-6">
            <h2 className="text-xl font-semibold text-gray-100 mb-4 flex items-center gap-2">
              <FiFileText className="h-5 w-5" />
              Generated Files
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {generatedFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-300 font-medium">{file.filename}</span>
                    <span className="text-gray-400 text-sm">{file.rows} rows</span>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {file.columns.slice(0, 5).map((col, colIdx) => (
                      <span
                        key={colIdx}
                        className="px-2 py-0.5 bg-gray-700/50 text-gray-400 text-xs rounded"
                      >
                        {col}
                      </span>
                    ))}
                    {file.columns.length > 5 && (
                      <span className="px-2 py-0.5 text-gray-500 text-xs">
                        +{file.columns.length - 5} more
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default DataGenerator
