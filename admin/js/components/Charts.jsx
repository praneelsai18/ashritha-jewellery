const { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } = Recharts;

window.SalesChart = ({ data }) => {
  return (
    <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm h-[400px]">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
            <lucide.Activity size={20} className="text-brand" />
            Business Insights
          </h3>
          <p className="text-sm text-gray-500 mt-1">Apr '26 - May '26</p>
        </div>
        <div className="flex bg-gray-100 rounded-lg p-1">
          <button className="px-4 py-1.5 text-sm font-medium bg-white shadow-sm rounded-md text-brand">Daily</button>
          <button className="px-4 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-900">Weekly</button>
        </div>
      </div>
      
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis 
              dataKey="date" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fontSize: 12, fill: '#6B7280' }} 
              dy={10}
            />
            <YAxis 
              axisLine={false} 
              tickLine={false} 
              tick={{ fontSize: 12, fill: '#6B7280' }}
              tickFormatter={(value) => `${value}`}
            />
            <Tooltip 
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            />
            <Line 
              type="monotone" 
              dataKey="sales" 
              stroke="#5B2D8E" 
              strokeWidth={3}
              dot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
              activeDot={{ r: 6, fill: '#5B2D8E', stroke: '#fff', strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

window.OrdersBarChart = ({ data }) => {
  return (
    <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm h-[400px]">
      <h3 className="text-lg font-bold text-gray-800 mb-6">Orders Overview</h3>
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} />
            <Tooltip cursor={{ fill: '#F3EEFF' }} contentStyle={{ borderRadius: '8px', border: 'none' }} />
            <Bar dataKey="orders" fill="#B8860B" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
