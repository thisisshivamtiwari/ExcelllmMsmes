import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { FiUpload, FiFile, FiX, FiCheckCircle, FiAlertCircle, FiLoader, FiRefreshCw, FiEye, FiTrash2 } from "react-icons/fi"

const FileUpload = () => {
  const [files, setFiles] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileData, setFileData] = useState(null)
  const [isLoadingData, setIsLoadingData] = useState(false)

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

  useEffect(() => {
    fetchFiles()
  }, [])

  const fetchFiles = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/files/list`)
      if (!response.ok) throw new Error("Failed to fetch files")
      const data = await response.json()
      setFiles(data.files || [])
    } catch (error) {
      console.error("Error fetching files:", error)
    }
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    setUploadStatus(null)

    const formData = new FormData()
    formData.append("file", file)

    try {
      const response = await fetch(`${API_BASE_URL}/files/upload`, {
        method: "POST",
        body: formData,
        headers: {
          // Don't set Content-Type, let browser set it with boundary for multipart/form-data
        },
      })

      const data = await response.json()

      if (response.ok) {
        setUploadStatus({
          type: "success",
          message: `File "${file.name}" uploaded successfully!`,
          warnings: data.warnings || [],
        })
        fetchFiles() // Refresh file list
        event.target.value = "" // Reset input
      } else {
        setUploadStatus({
          type: "error",
          message: data.detail?.message || data.detail || "Upload failed",
          errors: data.detail?.errors || [],
        })
      }
    } catch (error) {
      setUploadStatus({
        type: "error",
        message: `Error: ${error.message}`,
      })
    } finally {
      setIsUploading(false)
    }
  }

  const handleLoadFileData = async (fileId) => {
    setIsLoadingData(true)
    setFileData(null)
    setSelectedFile(fileId)

    try {
      const response = await fetch(`${API_BASE_URL}/files/${fileId}/load`)
      if (!response.ok) throw new Error("Failed to load file data")
      const data = await response.json()
      setFileData(data)
    } catch (error) {
      console.error("Error loading file data:", error)
      setUploadStatus({
        type: "error",
        message: `Error loading file: ${error.message}`,
      })
    } finally {
      setIsLoadingData(false)
    }
  }

  const handleDeleteFile = async (fileId) => {
    if (!confirm("Are you sure you want to delete this file?")) return

    try {
      const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
        method: "DELETE",
      })

      if (response.ok) {
        setUploadStatus({
          type: "success",
          message: "File deleted successfully",
        })
        fetchFiles()
        if (selectedFile === fileId) {
          setSelectedFile(null)
          setFileData(null)
        }
      } else {
        throw new Error("Failed to delete file")
      }
    } catch (error) {
      setUploadStatus({
        type: "error",
        message: `Error deleting file: ${error.message}`,
      })
    }
  }

  const handleViewMetadata = async (fileId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/files/${fileId}/metadata`)
      if (!response.ok) throw new Error("Failed to fetch metadata")
      const data = await response.json()
      setFileData({ type: "metadata", data })
      setSelectedFile(fileId)
    } catch (error) {
      console.error("Error fetching metadata:", error)
    }
  }

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-100 mb-2">File Upload & Management</h1>
          <p className="text-gray-400">
            Upload Excel (.xlsx, .xls) or CSV files for processing and analysis
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg mb-6">
          <h2 className="text-xl font-semibold text-gray-100 mb-4">Upload File</h2>
          
          <div className="flex flex-col md:flex-row items-center gap-4">
            <label className="flex-1 w-full md:w-auto">
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={handleFileUpload}
                disabled={isUploading}
                className="hidden"
                id="file-upload"
              />
              <Button
                as="span"
                disabled={isUploading}
                className="w-full md:w-auto cursor-pointer"
              >
                {isUploading ? (
                  <>
                    <FiLoader className="h-4 w-4 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <FiUpload className="h-4 w-4 mr-2" />
                    Choose File
                  </>
                )}
              </Button>
            </label>
            <p className="text-sm text-gray-400">
              Supported formats: .xlsx, .xls, .csv (Max 100MB)
            </p>
          </div>

          {/* Upload Status */}
          {uploadStatus && (
            <div
              className={`mt-4 p-4 rounded-lg border ${
                uploadStatus.type === "success"
                  ? "bg-green-900/20 border-green-700/50 text-green-300"
                  : "bg-red-900/20 border-red-700/50 text-red-300"
              }`}
            >
              <div className="flex items-start gap-2">
                {uploadStatus.type === "success" ? (
                  <FiCheckCircle className="h-5 w-5 mt-0.5 shrink-0" />
                ) : (
                  <FiAlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
                )}
                <div className="flex-1">
                  <p className="font-medium">{uploadStatus.message}</p>
                  {uploadStatus.warnings && uploadStatus.warnings.length > 0 && (
                    <ul className="mt-2 text-sm list-disc list-inside">
                      {uploadStatus.warnings.map((warning, idx) => (
                        <li key={idx}>{warning}</li>
                      ))}
                    </ul>
                  )}
                  {uploadStatus.errors && uploadStatus.errors.length > 0 && (
                    <ul className="mt-2 text-sm list-disc list-inside">
                      {uploadStatus.errors.map((error, idx) => (
                        <li key={idx}>{error}</li>
                      ))}
                    </ul>
                  )}
                </div>
                <button
                  onClick={() => setUploadStatus(null)}
                  className="text-gray-400 hover:text-gray-200"
                >
                  <FiX className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Files List */}
        <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg shadow-lg">
          <div className="p-6 border-b border-gray-800/50 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-100">Uploaded Files</h2>
            <button
              onClick={fetchFiles}
              className="p-2 text-gray-400 hover:text-gray-100 hover:bg-white/10 rounded-lg transition-colors"
              title="Refresh"
            >
              <FiRefreshCw className="h-5 w-5" />
            </button>
          </div>

          {files.length === 0 ? (
            <div className="p-12 text-center text-gray-400">
              <FiFile className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No files uploaded yet</p>
              <p className="text-sm mt-2">Upload a file to get started</p>
            </div>
          ) : (
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {files.map((file) => (
                  <div
                    key={file.file_id}
                    className={`bg-gray-800/50 border rounded-lg p-4 transition-all ${
                      selectedFile === file.file_id
                        ? "border-blue-500 bg-gray-800/70"
                        : "border-gray-700/50 hover:border-gray-600"
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-gray-100 truncate">
                          {file.filename}
                        </h3>
                        <p className="text-xs text-gray-400 mt-1">
                          {new Date(file.uploaded_at).toLocaleString()}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDeleteFile(file.file_id)}
                        className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                        title="Delete"
                      >
                        <FiTrash2 className="h-4 w-4" />
                      </button>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-gray-400 mb-3">
                      <span className="px-2 py-1 bg-gray-700/50 rounded">
                        {file.file_type?.toUpperCase() || "UNKNOWN"}
                      </span>
                      {file.row_count > 0 && (
                        <span>{file.row_count.toLocaleString()} rows</span>
                      )}
                      {file.column_count > 0 && (
                        <span>{file.column_count} cols</span>
                      )}
                    </div>

                    <div className="flex gap-2">
                      <Button
                        onClick={() => handleViewMetadata(file.file_id)}
                        variant="outline"
                        size="sm"
                        className="flex-1"
                      >
                        <FiEye className="h-3 w-3 mr-1" />
                        Metadata
                      </Button>
                      <Button
                        onClick={() => handleLoadFileData(file.file_id)}
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        disabled={isLoadingData && selectedFile === file.file_id}
                      >
                        {isLoadingData && selectedFile === file.file_id ? (
                          <FiLoader className="h-3 w-3 mr-1 animate-spin" />
                        ) : (
                          <FiFile className="h-3 w-3 mr-1" />
                        )}
                        Preview
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* File Data Preview */}
        {fileData && (
          <div className="mt-6 bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg shadow-lg">
            <div className="p-6 border-b border-gray-800/50 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-100">
                {fileData.type === "metadata" ? "File Metadata" : "File Preview"}
              </h2>
              <button
                onClick={() => {
                  setFileData(null)
                  setSelectedFile(null)
                }}
                className="text-gray-400 hover:text-gray-200"
              >
                <FiX className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6">
              {fileData.type === "metadata" ? (
                <pre className="bg-gray-950/50 p-4 rounded-lg overflow-x-auto text-sm text-gray-300 font-mono">
                  {JSON.stringify(fileData.data, null, 2)}
                </pre>
              ) : (
                <div className="overflow-x-auto">
                  {typeof fileData.data === "object" && !Array.isArray(fileData.data) ? (
                    // Excel file with multiple sheets
                    <div className="space-y-4">
                      {Object.entries(fileData.data).map(([sheet, rows]) => (
                        <div key={sheet}>
                          <h3 className="text-lg font-semibold text-gray-100 mb-2">
                            Sheet: {sheet}
                          </h3>
                          <div className="overflow-x-auto">
                            <table className="min-w-full border border-gray-700">
                              <thead>
                                <tr className="bg-gray-800/50">
                                  {rows.length > 0 &&
                                    Object.keys(rows[0]).map((col) => (
                                      <th
                                        key={col}
                                        className="px-4 py-2 text-left text-xs font-medium text-gray-300 border-b border-gray-700"
                                      >
                                        {col}
                                      </th>
                                    ))}
                                </tr>
                              </thead>
                              <tbody>
                                {rows.slice(0, 10).map((row, idx) => (
                                  <tr key={idx} className="border-b border-gray-800">
                                    {Object.values(row).map((val, colIdx) => (
                                      <td
                                        key={colIdx}
                                        className="px-4 py-2 text-sm text-gray-400"
                                      >
                                        {String(val)}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            {rows.length > 10 && (
                              <p className="text-xs text-gray-500 mt-2">
                                Showing first 10 rows of {rows.length} total rows
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    // CSV file
                    <div className="overflow-x-auto">
                      <table className="min-w-full border border-gray-700">
                        <thead>
                          <tr className="bg-gray-800/50">
                            {fileData.data.length > 0 &&
                              Object.keys(fileData.data[0]).map((col) => (
                                <th
                                  key={col}
                                  className="px-4 py-2 text-left text-xs font-medium text-gray-300 border-b border-gray-700"
                                >
                                  {col}
                                </th>
                              ))}
                          </tr>
                        </thead>
                        <tbody>
                          {fileData.data.slice(0, 10).map((row, idx) => (
                            <tr key={idx} className="border-b border-gray-800">
                              {Object.values(row).map((val, colIdx) => (
                                <td
                                  key={colIdx}
                                  className="px-4 py-2 text-sm text-gray-400"
                                >
                                  {String(val)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {fileData.data.length > 10 && (
                        <p className="text-xs text-gray-500 mt-2">
                          Showing first 10 rows of {fileData.data.length} total rows
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default FileUpload

