import { useState } from "react"
import { FiImage, FiX, FiMaximize2 } from "react-icons/fi"

const VisualizationImages = ({ images, title = "Visualizations", loading = false }) => {
  const [selectedImage, setSelectedImage] = useState(null)
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

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
    if (url.startsWith("http")) return url
    if (url.startsWith("/")) return `${API_BASE_URL}${url}`
    return `${API_BASE_URL}/${url}`
  }

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
          {images.map((image, idx) => (
            <div
              key={idx}
              className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden hover:border-gray-600 transition-colors cursor-pointer group"
              onClick={() => handleImageClick(image.url)}
            >
              <div className="relative aspect-video bg-gray-900">
                <img
                  src={getImageUrl(image.url)}
                  alt={image.name || `Visualization ${idx + 1}`}
                  className="w-full h-full object-contain"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                  <FiMaximize2 className="h-6 w-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </div>
              <div className="p-3">
                <p className="text-sm font-medium text-gray-300 truncate">
                  {image.name || `Visualization ${idx + 1}`}
                </p>
              </div>
            </div>
          ))}
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

