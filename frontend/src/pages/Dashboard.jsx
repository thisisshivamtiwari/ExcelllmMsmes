const Dashboard = () => {
  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-100 mb-2">Dashboard</h1>
        <p className="text-gray-400 mb-8">Welcome to your analytics dashboard</p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
            <h3 className="text-gray-400 text-sm mb-2">Total Files</h3>
            <p className="text-3xl font-bold text-gray-100">24</p>
          </div>
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
            <h3 className="text-gray-400 text-sm mb-2">Total Queries</h3>
            <p className="text-3xl font-bold text-gray-100">156</p>
          </div>
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
            <h3 className="text-gray-400 text-sm mb-2">Analytics</h3>
            <p className="text-3xl font-bold text-gray-100">89%</p>
          </div>
          <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/50 rounded-lg p-6 shadow-lg">
            <h3 className="text-gray-400 text-sm mb-2">Reports</h3>
            <p className="text-3xl font-bold text-gray-100">12</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard


