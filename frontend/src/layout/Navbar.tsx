import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Home, AlarmClock, Settings } from "lucide-react";
import { getNavbarRoutes } from "../config/routeConfig";

const NavbarComponent: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [currentPath, setCurrentPath] = useState(location.pathname);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  // Update currentPath whenever location changes
  useEffect(() => {
    setCurrentPath(location.pathname);
  }, [location.pathname]);

  const navbarRoutes = getNavbarRoutes();

  const handleNavigation = (path: string) => {
    navigate(path);
    setCurrentPath(path);
  };

  const isRouteActive = (routePath: string) => {
    const isActive =
      currentPath === routePath ||
      (routePath === "/" && currentPath === "/home") ||
      (routePath === "/home" && currentPath === "/");

    return isActive;
  };

  // Map icon names to components
  const getIconComponent = (iconName: string | undefined) => {
    switch (iconName) {
      case "home-icon":
        return <Home size={22} />;
      case "alarm-icon":
        return <AlarmClock size={22} />;
      case "settings-icon":
        return <Settings size={22} />;
      default:
        return <Home size={22} />;
    }
  };

  return (
    <nav
      className="fixed left-0 right-0 bottom-0 w-full bg-gray-900 px-4 py-3 shadow-xl z-[1045] border-t border-gray-800
                    md:bottom-6 md:left-1/2 md:right-auto md:translate-x-[-50%]
                    md:w-[90%] md:max-w-[500px] md:rounded-2xl md:border-t-0"
    >
      <div className="grid grid-cols-3 gap-2 w-full">
        {navbarRoutes.map((route, idx) => {
          // Pre-compute the active state
          const isActive = isRouteActive(route.path);

          return (
            <div
              key={route.path}
              onClick={() => handleNavigation(route.path)}
              onTouchEnd={() => handleNavigation(route.path)} // Add touch event handler for mobile
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              className={`flex flex-col items-center py-1 px-2 rounded-lg cursor-pointer transition-all duration-200 space-y-1
                        ${isActive ? "!text-teal-400" : "text-gray-400"}
                        ${hoveredIdx === idx ? "bg-gray-800" : ""}`}
            >
              <div className={`flex items-center justify-center ${isActive ? "text-teal-400" : ""}`}>
                {getIconComponent(route.icon)}
              </div>
              <span className={`text-xs font-medium select-none ${isActive ? "text-teal-400" : ""}`}>
                {route.title}
              </span>
            </div>
          );
        })}
      </div>
    </nav>
  );
};

export default NavbarComponent;
