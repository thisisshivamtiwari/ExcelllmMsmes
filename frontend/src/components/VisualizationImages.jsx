import { useState } from "react"
import { FiImage, FiX, FiMaximize2 } from "react-icons/fi"

const VisualizationImages = ({ images, title = "Saved Visualizations", loading = false }) => {
  const [selectedImage, setSelectedImage] = useState(null)
  const [imageErrors, setImageErrors] = useState({})
  
  // Get API base URL - handle both with and without /api suffix
  const envApiUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"
  const API_BASE_URL = envApiUrl.endsWith("/api") ? envApiUrl.replace("/api", "") : envApiUrl

  if (loading) {
    return (
      <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg">
        <h3 className="text-xl font-semibold text-gray-100 mb-6 flex items-center gap-2">
          <FiImage className="h-5 w-5 text-blue-400" />
          {title}
        </h3>
        <div className="text-center py-8 text-gray-400">
          <p>Loading visualizations...</p>
        </div>
      </div>
    )
  }

  if (!images || images.length === 0) {
    return (
      <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg">
        <h3 className="text-xl font-semibold text-gray-100 mb-6 flex items-center gap-2">
          <FiImage className="h-5 w-5 text-blue-400" />
          {title}
        </h3>
        <div className="text-center py-8 text-gray-400">
          <p>No saved visualizations found.</p>
          <p className="text-sm mt-2">Visualizations will appear here after running analyses.</p>
        </div>
      </div>
    )
  }

  // Ensure URLs are absolute
  const getImageUrl = (url) => {
    if (!url) {
      console.warn("VisualizationImages: Empty URL provided")
      return ""
    }
    if (url.startsWith("http://") || url.startsWith("https://")) return url
    // If URL starts with /api, prepend base URL
    if (url.startsWith("/api/")) {
      const fullUrl = `${API_BASE_URL}${url}`
      console.log(`VisualizationImages: Constructed URL: ${fullUrl} (from ${url})`)
      return fullUrl
    }
    // If URL starts with /, prepend base URL
    if (url.startsWith("/")) {
      const fullUrl = `${API_BASE_URL}${url}`
      console.log(`VisualizationImages: Constructed URL: ${fullUrl} (from ${url})`)
      return fullUrl
    }
    // Otherwise, assume it's a relative path
    const fullUrl = `${API_BASE_URL}/api/${url}`
    console.log(`VisualizationImages: Constructed URL: ${fullUrl} (from ${url})`)
    return fullUrl
  }

  const handleImageError = (index, imageUrl) => {
    console.error(`VisualizationImages: Failed to load image at index ${index}: ${imageUrl}`)
    setImageErrors(prev => ({ ...prev, [index]: true }))
  }

  // Debug: Log images prop
  console.log(`VisualizationImages: Received ${images?.length || 0} images`, images)

  const handleImageClick = (imageUrl) => {
    setSelectedImage(imageUrl)
  }

  const closeModal = () => {
    setSelectedImage(null)
  }

  return (
    <>
      <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-4 md:p-6 shadow-lg">
        <h3 className="text-xl font-semibold text-gray-100 mb-6 flex items-center gap-2">
          <FiImage className="h-5 w-5 text-blue-400" />
          {title}
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {images.map((image, idx) => {
            // API returns: {name, path, size, modified}
            // Support both old format (url/filename) and new format (path/name)
            const imageUrl = getImageUrl(image.path || image.url || image.filename)
            const imageName = image.name || image.filename || `Visualization ${idx + 1}`
            const hasError = imageErrors[idx]
            
            return (
              <div
                key={idx}
                className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden hover:border-gray-600 transition-colors cursor-pointer group"
                onClick={() => handleImageClick(imageUrl)}
              >
                <div className="relative aspect-video bg-gray-900">
                  {hasError ? (
                    <div className="w-full h-full flex items-center justify-center text-gray-500">
                      <div className="text-center">
                        <FiImage className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p className="text-xs">Failed to load</p>
                        <p className="text-xs mt-1 text-gray-600">{imageUrl}</p>
                      </div>
                    </div>
                  ) : (
                    <>
                      <img
                        src={imageUrl}
                        alt={imageName}
                        className="w-full h-full object-contain"
                        loading="lazy"
                        onError={() => handleImageError(idx, imageUrl)}
                      />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                        <FiMaximize2 className="h-6 w-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    </>
                  )}
                </div>
                <div className="p-3">
                  <p className="text-sm font-medium text-gray-300 truncate">
                    {imageName}
                  </p>
                  {image.size && (
                    <p className="text-xs text-gray-500 mt-1">
                      {(image.size / 1024).toFixed(1)} KB
                    </p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Modal for full-size image */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={closeModal}
        >
          <div className="relative max-w-7xl max-h-full">
            <button
              onClick={closeModal}
              className="absolute top-4 right-4 z-10 bg-gray-900/90 hover:bg-gray-800 rounded-full p-2 text-gray-300 hover:text-white transition-colors"
              aria-label="Close"
            >
              <FiX className="h-6 w-6" />
            </button>
            <img
              src={getImageUrl(selectedImage)}
              alt="Full size visualization"
              className="max-w-full max-h-[90vh] object-contain rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </>
  )
}

export default VisualizationImages

