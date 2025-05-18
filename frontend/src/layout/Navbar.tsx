import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Home, AlarmClock, Settings } from "lucide-react";

const NavbarComponent: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname;

  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  const isRouteActive = (routePath: string) => {
    return (
      currentPath === routePath ||
      (routePath === "/" && currentPath === "/home") ||
      (routePath === "/home" && currentPath === "/")
    );
  };

  const navItems = [
    { path: "/", icon: <Home size={22} />, label: "Home" },
    { path: "/alarm", icon: <AlarmClock size={22} />, label: "Wecker" },
    { path: "/config", icon: <Settings size={22} />, label: "Einstellungen" },
  ];

  return (
    <nav
      className="fixed left-0 right-0 bottom-0 w-full bg-gray-900 px-4 py-2 shadow-xl z-[1045] border-t border-gray-800
                    md:bottom-6 md:left-1/2 md:right-auto md:translate-x-[-50%]
                    md:w-[90%] md:max-w-[500px] md:rounded-2xl md:border-t-0"
    >
      <div className="grid grid-cols-3 gap-2 w-full">
        {navItems.map((item, idx) => (
          <div
            key={item.path}
            onClick={() => handleNavigation(item.path)}
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
            className={`flex flex-col items-center py-2 px-2 rounded-lg cursor-pointer transition-all duration-200 space-y-1
                       ${isRouteActive(item.path) ? "text-teal-400" : "text-gray-400"}
                       ${hoveredIdx === idx ? "bg-gray-800 text-white" : ""}`}
          >
            <div className="flex items-center justify-center">{item.icon}</div>
            <span className="text-xs font-medium">{item.label}</span>
            {isRouteActive(item.path)}
          </div>
        ))}
      </div>
    </nav>
  );
};

export default NavbarComponent;
