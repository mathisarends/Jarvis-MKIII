import { useState } from "react";
import { Home, AlarmClock, MessageSquare, BarChart3, User } from "lucide-react";

interface NavItem {
  route: string;
  icon: "home" | "alarm" | "messages" | "stats" | "profile";
  label: string;
}

const NavbarComponent: React.FC = () => {
  const [activeRoute, setActiveRoute] = useState<string>("/home");

  const navItems: NavItem[] = [
    { route: "/home", icon: "home", label: "Home" },
    { route: "/alarm", icon: "alarm", label: "Wecker" },
    { route: "/messages", icon: "messages", label: "Nachrichten" },
    { route: "/stats", icon: "stats", label: "Statistik" },
    { route: "/profile", icon: "profile", label: "Profil" },
  ];

  const handleSetActive = (route: string) => {
    setActiveRoute(route);
  };

  const renderIcon = (iconName: string, isActive: boolean, isHovered: boolean) => {
    const iconColor = isActive || isHovered ? "#FFFFFF" : "#9CA3AF";
    const bgColor = isActive || isHovered ? "bg-[#2D3748]" : "bg-transparent";
    const indicatorColor = isActive ? "bg-teal-500" : "bg-transparent";
    const size = 24;

    return (
      <div className={`relative flex flex-col items-center`}>
        <div className={`p-4 rounded-xl transition-colors duration-200 ${bgColor}`}>
          {iconName === "home" && <Home size={size} color={iconColor} />}
          {iconName === "alarm" && <AlarmClock size={size} color={iconColor} />}
          {iconName === "messages" && <MessageSquare size={size} color={iconColor} />}
          {iconName === "stats" && <BarChart3 size={size} color={iconColor} />}
          {iconName === "profile" && <User size={size} color={iconColor} />}
        </div>
        <div className={`absolute -bottom-1 h-1 w-10 rounded-full ${indicatorColor}`}></div>
      </div>
    );
  };

  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  return (
    <div
      className="
      fixed 
      left-0 right-0 bottom-0 
      w-full py-3 bg-[#1A202C] flex items-center justify-between px-5 shadow-xl z-[1045]
      md:bottom-10 
      md:left-1/2 md:right-auto md:translate-x-[-50%]
      md:w-[92%] md:max-w-[500px] md:rounded-3xl md:px-8
      mx-auto
      "
    >
      {navItems.map((item, idx) => (
        <div
          key={item.route}
          onClick={() => handleSetActive(item.route)}
          onMouseEnter={() => setHoveredIdx(idx)}
          onMouseLeave={() => setHoveredIdx(null)}
          className="flex items-center justify-center cursor-pointer relative select-none transition-all duration-300"
        >
          {renderIcon(item.icon, activeRoute === item.route, hoveredIdx === idx)}
        </div>
      ))}
    </div>
  );
};

export default NavbarComponent;
