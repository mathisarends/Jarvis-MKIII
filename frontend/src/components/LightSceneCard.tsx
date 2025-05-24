import React from "react";
import { Zap, Star, Flower2, Gem, Clover, Sun, Sunrise, Sunset, Check, type LucideIcon } from "lucide-react";

interface SceneTailwindConfig {
  icon: LucideIcon;
  bgClass: string;
  textClass: string;
  hoverClass: string;
  activeBgClass: string;
  activeTextClass: string;
  activeBorderClass: string;
}

export const sceneTailwindMapping: Record<string, SceneTailwindConfig> = {
  Nordlichter: {
    icon: Zap,
    bgClass: "bg-blue-50",
    textClass: "text-blue-800",
    hoverClass: "hover:bg-blue-100",
    activeBgClass: "bg-blue-700",
    activeTextClass: "text-blue-100",
    activeBorderClass: "border-blue-800",
  },
  Sternenlicht: {
    icon: Star,
    bgClass: "bg-slate-50",
    textClass: "text-slate-700",
    hoverClass: "hover:bg-slate-100",
    activeBgClass: "bg-slate-800",
    activeTextClass: "text-amber-300",
    activeBorderClass: "border-slate-900",
  },
  Blossom: {
    icon: Flower2,
    bgClass: "bg-pink-50",
    textClass: "text-pink-700",
    hoverClass: "hover:bg-pink-100",
    activeBgClass: "bg-pink-600",
    activeTextClass: "text-pink-100",
    activeBorderClass: "border-pink-700",
  },
  Wertvoll: {
    icon: Gem,
    bgClass: "bg-amber-50",
    textClass: "text-amber-800",
    hoverClass: "hover:bg-amber-100",
    activeBgClass: "bg-amber-700",
    activeTextClass: "text-amber-100",
    activeBorderClass: "border-amber-800",
  },
  Schleierkraut: {
    icon: Clover,
    bgClass: "bg-green-50",
    textClass: "text-green-700",
    hoverClass: "hover:bg-green-100",
    activeBgClass: "bg-green-600",
    activeTextClass: "text-green-100",
    activeBorderClass: "border-green-700",
  },
  Bernsteinblüte: {
    icon: Sun,
    bgClass: "bg-orange-50",
    textClass: "text-orange-800",
    hoverClass: "hover:bg-orange-100",
    activeBgClass: "bg-orange-600",
    activeTextClass: "text-orange-100",
    activeBorderClass: "border-orange-700",
  },
  "Majestätischer Morgen": {
    icon: Sunrise,
    bgClass: "bg-yellow-50",
    textClass: "text-yellow-800",
    hoverClass: "hover:bg-yellow-100",
    activeBgClass: "bg-yellow-600",
    activeTextClass: "text-yellow-100",
    activeBorderClass: "border-yellow-700",
  },
  "Verträumter Sonnenuntergang": {
    icon: Sunset,
    bgClass: "bg-red-50",
    textClass: "text-red-700",
    hoverClass: "hover:bg-red-100",
    activeBgClass: "bg-red-600",
    activeTextClass: "text-red-100",
    activeBorderClass: "border-red-700",
  },
};

export const defaultSceneTailwindConfig: SceneTailwindConfig = {
  icon: Sun,
  bgClass: "bg-gray-50",
  textClass: "text-gray-700",
  hoverClass: "hover:bg-gray-100",
  activeBgClass: "bg-gray-500",
  activeTextClass: "text-white",
  activeBorderClass: "border-gray-600",
};

export const getSceneTailwindConfig = (sceneName: string): SceneTailwindConfig => {
  return sceneTailwindMapping[sceneName] || defaultSceneTailwindConfig;
};

interface LightSceneCardProps {
  sceneName: string;
  isActive?: boolean;
  onClick?: () => void;
}

const LightSceneCard: React.FC<LightSceneCardProps> = ({ sceneName, isActive = false, onClick }) => {
  const config = getSceneTailwindConfig(sceneName);
  const IconComponent = config.icon;

  return (
    <div
      className={`
        relative p-4 rounded-xl cursor-pointer transition-all duration-200 transform hover:scale-[1.02] shadow-sm border-2 min-h-[80px]
        ${
          isActive
            ? `${config.activeBgClass} ${config.activeTextClass} ${config.activeBorderClass} shadow-lg scale-[1.02]`
            : `${config.bgClass} ${config.textClass} border-transparent ${config.hoverClass} hover:shadow-md`
        }
      `}
      onClick={onClick}
    >
      {/* Active Indicator */}
      {isActive && (
        <div className="absolute top-2 right-2">
          <Check size={16} className="font-bold" />
        </div>
      )}

      <div className="flex items-center space-x-3">
        <IconComponent size={20} className="flex-shrink-0" />
        <span className="font-medium text-sm leading-tight">{sceneName}</span>
      </div>
    </div>
  );
};

export default LightSceneCard;
