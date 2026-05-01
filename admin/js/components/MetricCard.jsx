const { TrendingUp, TrendingDown, Clock, Package, DollarSign, Activity } = lucide;

window.MetricCard = ({ title, value, growth, prefix, suffix, iconType }) => {
  const isPositive = growth > 0;
  const isNeutral = growth === 0;
  
  const getIcon = () => {
    switch(iconType) {
      case 'orders': return <Package className="text-blue-500" size={24} />;
      case 'sales': return <DollarSign className="text-green-500" size={24} />;
      case 'conversion': return <Activity className="text-purple-500" size={24} />;
      case 'views': return <Clock className="text-orange-500" size={24} />;
      default: return <Activity className="text-gray-500" size={24} />;
    }
  };

  const getBgColor = () => {
    switch(iconType) {
      case 'orders': return 'bg-blue-50';
      case 'sales': return 'bg-green-50';
      case 'conversion': return 'bg-purple-50';
      case 'views': return 'bg-orange-50';
      default: return 'bg-gray-50';
    }
  };

  return (
    <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <h3 className="text-2xl font-bold text-gray-900 mt-1">
            {prefix}{value}{suffix}
          </h3>
        </div>
        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${getBgColor()}`}>
          {getIcon()}
        </div>
      </div>
      
      <div className="mt-4 flex items-center gap-2">
        {!isNeutral && (
          <span className={`flex items-center text-xs font-semibold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {isPositive ? <TrendingUp size={14} className="mr-1" /> : <TrendingDown size={14} className="mr-1" />}
            {Math.abs(growth)}%
          </span>
        )}
        <span className="text-xs text-gray-400">vs last 7 days</span>
      </div>
    </div>
  );
};
