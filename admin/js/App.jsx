const { useState, useEffect } = React;
const { createRoot } = ReactDOM;

const App = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const data = window.DashboardData;

  // Render dummy data metrics for top cards
  const metrics = [
    { title: "Total Views", value: "45,930", growth: 12.5, prefix: "", suffix: "", icon: "views" },
    { title: "Total Clicks", value: "1,105", growth: 5.2, prefix: "", suffix: "", icon: "views" },
    { title: "Total Orders", value: "1", growth: -2.1, prefix: "", suffix: "", icon: "orders" },
    { title: "Conversion Rate", value: "2.2", growth: 0.5, prefix: "", suffix: "%", icon: "conversion" },
    { title: "Total Sales", value: "276", growth: 15.3, prefix: "₹", suffix: "", icon: "sales" },
    { title: "Return Percentage", value: "0", growth: 0, prefix: "", suffix: "%", icon: "views" },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-[#F8F9FA]">
      <window.Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />
      
      <div className="flex-1 flex flex-col h-screen overflow-hidden relative">
        <window.Header setIsSidebarOpen={setIsSidebarOpen} />
        
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 custom-scrollbar">
          <div className="max-w-7xl mx-auto space-y-6">
            
            {/* Page Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Business Dashboard</h1>
                <p className="text-sm text-gray-500 mt-1">Welcome back, here's what's happening with your store today.</p>
              </div>
              
              <div className="flex bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
                <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 border-r border-gray-200">Yesterday</button>
                <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 border-r border-gray-200">Last 7 Days</button>
                <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 border-r border-gray-200">Last 30 Days</button>
                <button className="px-4 py-2 text-sm font-medium bg-brand-light text-brand">Custom Date</button>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
              {metrics.map((metric, idx) => (
                <window.MetricCard 
                  key={idx}
                  title={metric.title}
                  value={metric.value}
                  growth={metric.growth}
                  prefix={metric.prefix}
                  suffix={metric.suffix}
                  iconType={metric.icon}
                />
              ))}
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <window.SalesChart data={data.salesTrendData} />
              </div>
              <div className="lg:col-span-1">
                <window.OrdersBarChart data={data.salesTrendData} />
              </div>
            </div>

            {/* Product Table */}
            <div className="pb-8">
              <window.ProductTable data={data.productPerformance} />
            </div>

          </div>
        </main>
      </div>
    </div>
  );
};

// Initialize App
const root = createRoot(document.getElementById('root'));
root.render(<App />);
