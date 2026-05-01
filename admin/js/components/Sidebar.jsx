const { Home, ShoppingBag, Users, Settings, Package, PieChart, Bell, ChevronLeft, Menu } = lucide;

window.Sidebar = ({ isOpen, setIsOpen }) => {
  const menuItems = [
    { name: 'Dashboard', icon: <Home size={20} />, active: true },
    { name: 'Orders', icon: <ShoppingBag size={20} /> },
    { name: 'Products', icon: <Package size={20} /> },
    { name: 'Customers', icon: <Users size={20} /> },
    { name: 'Analytics', icon: <PieChart size={20} /> },
    { name: 'Settings', icon: <Settings size={20} /> },
  ];

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}
      
      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 bg-white border-r border-gray-200
        transform transition-transform duration-200 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="h-16 flex items-center justify-between px-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center">
              <span className="text-white font-bold font-serif italic text-sm">A</span>
            </div>
            <span className="font-bold text-lg text-gray-800">Ashritha</span>
          </div>
          <button 
            onClick={() => setIsOpen(false)}
            className="p-1 rounded-md text-gray-500 hover:bg-gray-100 lg:hidden"
          >
            <ChevronLeft size={20} />
          </button>
        </div>

        <nav className="p-4 space-y-1">
          {menuItems.map((item, idx) => (
            <a
              key={idx}
              href="#"
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                ${item.active 
                  ? 'bg-brand-light text-brand' 
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}
              `}
            >
              {item.icon}
              {item.name}
            </a>
          ))}
        </nav>
      </aside>
    </>
  );
};
