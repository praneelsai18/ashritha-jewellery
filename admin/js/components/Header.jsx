const { Menu, Bell, Search } = lucide;

window.Header = ({ setIsSidebarOpen }) => {
  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 sm:px-6 z-10 sticky top-0">
      <div className="flex items-center gap-4">
        <button 
          onClick={() => setIsSidebarOpen(true)}
          className="p-2 -ml-2 rounded-md text-gray-500 hover:bg-gray-100 lg:hidden"
        >
          <Menu size={20} />
        </button>
        
        <div className="hidden sm:flex items-center bg-gray-100 rounded-full px-4 py-2 w-64 border border-transparent focus-within:border-brand focus-within:bg-white transition-all">
          <Search size={16} className="text-gray-400" />
          <input 
            type="text" 
            placeholder="Search..." 
            className="bg-transparent border-none outline-none ml-2 text-sm w-full"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="relative p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors">
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
        </button>
        
        <div className="h-8 w-px bg-gray-200 mx-1"></div>
        
        <button className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-brand text-white flex items-center justify-center font-bold text-sm">
            A
          </div>
          <div className="hidden sm:block text-left">
            <p className="text-sm font-semibold text-gray-700 leading-none">Admin User</p>
            <p className="text-xs text-gray-500 mt-1">admin@ashritha.com</p>
          </div>
        </button>
      </div>
    </header>
  );
};
