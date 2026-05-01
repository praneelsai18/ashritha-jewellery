const { Search, TrendingUp, TrendingDown, Info } = lucide;

window.ProductTable = ({ data }) => {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="p-5 border-b border-gray-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h3 className="text-lg font-bold text-gray-800">Product Performance</h3>
          <p className="text-sm text-gray-500 mt-1">24th Apr '26 - 30th Apr '26</p>
        </div>
        <div className="relative w-full sm:w-64">
          <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input 
            type="text" 
            placeholder="Search by Product ID or Name" 
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand"
          />
        </div>
      </div>
      
      {/* Tabs */}
      <div className="flex border-b border-gray-100 overflow-x-auto custom-scrollbar">
        <button className="px-6 py-3 text-sm font-semibold text-brand border-b-2 border-brand whitespace-nowrap">All (13)</button>
        <button className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 whitespace-nowrap">Low Orders (0)</button>
        <button className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 whitespace-nowrap">Low Views (0)</button>
        <button className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 whitespace-nowrap">Low Conversion Rate (0)</button>
      </div>

      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wider font-semibold border-b border-gray-100">
              <th className="p-4 pl-6 font-medium">Product Details</th>
              <th className="p-4 font-medium text-center">Views</th>
              <th className="p-4 font-medium text-center">Clicks</th>
              <th className="p-4 font-medium text-center">Orders</th>
              <th className="p-4 font-medium text-center">Conversions</th>
              <th className="p-4 font-medium text-right">Sales</th>
              <th className="p-4 font-medium text-right pr-6">Returns</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {data.map((product, idx) => (
              <tr key={idx} className="hover:bg-gray-50/50 transition-colors">
                <td className="p-4 pl-6">
                  <div className="flex items-center gap-4">
                    <img src={product.image} alt={product.name} className="w-12 h-12 rounded-lg object-cover border border-gray-200" />
                    <div>
                      <p className="text-sm font-semibold text-gray-800 line-clamp-2 max-w-[250px]">{product.name}</p>
                      <p className="text-xs text-gray-400 mt-0.5">ID: {product.id}</p>
                    </div>
                  </div>
                </td>
                <td className="p-4 text-center">
                  <p className="text-sm font-medium text-gray-800">{product.views}</p>
                  <p className={`text-xs mt-1 flex items-center justify-center gap-1 font-semibold ${product.viewsGrowth >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {product.viewsGrowth >= 0 ? <TrendingUp size={12}/> : <TrendingDown size={12}/>}
                    {Math.abs(product.viewsGrowth)}%
                  </p>
                </td>
                <td className="p-4 text-center text-sm text-gray-600">{product.clicks}</td>
                <td className="p-4 text-center text-sm text-gray-600">{product.orders}</td>
                <td className="p-4 text-center text-sm text-gray-600">{product.conversion.toFixed(1)}%</td>
                <td className="p-4 text-right text-sm font-medium text-gray-800">₹{product.sales.toFixed(2)}</td>
                <td className="p-4 text-right pr-6 text-sm text-gray-600">{product.returns.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
