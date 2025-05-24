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
  gradientClass: string;
  shadowClass: string;
}

export const sceneTailwindMapping: Record<string, SceneTailwindConfig> = {
  Nordlichter: {
    icon: Zap,
    bgClass: "bg-gradient-to-br from-blue-50 to-cyan-50",
    textClass: "text-blue-800",
    hoverClass: "hover:from-blue-100 hover:to-cyan-100",
    activeBgClass: "bg-gradient-to-br from-blue-600 to-cyan-600",
    activeTextClass: "text-white",
    activeBorderClass: "border-blue-500",
    gradientClass: "bg-gradient-to-br from-blue-400/20 to-cyan-400/20",
    shadowClass: "shadow-blue-200/50",
  },
  Sternenlicht: {
    icon: Star,
    bgClass: "bg-gradient-to-br from-slate-50 to-gray-50",
    textClass: "text-slate-700",
    hoverClass: "hover:from-slate-100 hover:to-gray-100",
    activeBgClass: "bg-gradient-to-br from-slate-700 to-gray-800",
    activeTextClass: "text-amber-200",
    activeBorderClass: "border-slate-600",
    gradientClass: "bg-gradient-to-br from-slate-400/20 to-gray-400/20",
    shadowClass: "shadow-slate-200/50",
  },
  Blossom: {
    icon: Flower2,
    bgClass: "bg-gradient-to-br from-pink-50 to-rose-50",
    textClass: "text-pink-700",
    hoverClass: "hover:from-pink-100 hover:to-rose-100",
    activeBgClass: "bg-gradient-to-br from-pink-500 to-rose-500",
    activeTextClass: "text-pink-50",
    activeBorderClass: "border-pink-400",
    gradientClass: "bg-gradient-to-br from-pink-400/20 to-rose-400/20",
    shadowClass: "shadow-pink-200/50",
  },
  Wertvoll: {
    icon: Gem,
    bgClass: "bg-gradient-to-br from-amber-50 to-yellow-50",
    textClass: "text-amber-800",
    hoverClass: "hover:from-amber-100 hover:to-yellow-100",
    activeBgClass: "bg-gradient-to-br from-amber-500 to-yellow-500",
    activeTextClass: "text-amber-50",
    activeBorderClass: "border-amber-400",
    gradientClass: "bg-gradient-to-br from-amber-400/20 to-yellow-400/20",
    shadowClass: "shadow-amber-200/50",
  },
  Schleierkraut: {
    icon: Clover,
    bgClass: "bg-gradient-to-br from-green-50 to-emerald-50",
    textClass: "text-green-700",
    hoverClass: "hover:from-green-100 hover:to-emerald-100",
    activeBgClass: "bg-gradient-to-br from-green-500 to-emerald-500",
    activeTextClass: "text-green-50",
    activeBorderClass: "border-green-400",
    gradientClass: "bg-gradient-to-br from-green-400/20 to-emerald-400/20",
    shadowClass: "shadow-green-200/50",
  },
  Bernsteinblüte: {
    icon: Sun,
    bgClass: "bg-gradient-to-br from-orange-50 to-amber-50",
    textClass: "text-orange-800",
    hoverClass: "hover:from-orange-100 hover:to-amber-100",
    activeBgClass: "bg-gradient-to-br from-orange-500 to-amber-500",
    activeTextClass: "text-orange-50",
    activeBorderClass: "border-orange-400",
    gradientClass: "bg-gradient-to-br from-orange-400/20 to-amber-400/20",
    shadowClass: "shadow-orange-200/50",
  },
  "Majestätischer Morgen": {
    icon: Sunrise,
    bgClass: "bg-gradient-to-br from-yellow-50 to-orange-50",
    textClass: "text-yellow-800",
    hoverClass: "hover:from-yellow-100 hover:to-orange-100",
    activeBgClass: "bg-gradient-to-br from-yellow-500 to-orange-500",
    activeTextClass: "text-yellow-50",
    activeBorderClass: "border-yellow-400",
    gradientClass: "bg-gradient-to-br from-yellow-400/20 to-orange-400/20",
    shadowClass: "shadow-yellow-200/50",
  },
  "Verträumter Sonnenuntergang": {
    icon: Sunset,
    bgClass: "bg-gradient-to-br from-red-50 to-pink-50",
    textClass: "text-red-700",
    hoverClass: "hover:from-red-100 hover:to-pink-100",
    activeBgClass: "bg-gradient-to-br from-red-500 to-pink-500",
    activeTextClass: "text-red-50",
    activeBorderClass: "border-red-400",
    gradientClass: "bg-gradient-to-br from-red-400/20 to-pink-400/20",
    shadowClass: "shadow-red-200/50",
  },
};

export const defaultSceneTailwindConfig: SceneTailwindConfig = {
  icon: Sun,
  bgClass: "bg-gradient-to-br from-gray-50 to-slate-50",
  textClass: "text-gray-700",
  hoverClass: "hover:from-gray-100 hover:to-slate-100",
  activeBgClass: "bg-gradient-to-br from-gray-500 to-slate-500",
  activeTextClass: "text-white",
  activeBorderClass: "border-gray-400",
  gradientClass: "bg-gradient-to-br from-gray-400/20 to-slate-400/20",
  shadowClass: "shadow-gray-200/50",
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
        group relative p-5 rounded-2xl cursor-pointer transition-all duration-300 transform border-2 min-h-[100px] overflow-hidden
        ${
          isActive
            ? `${config.activeBgClass} ${config.activeTextClass} ${config.activeBorderClass} shadow-xl ${config.shadowClass}`
            : `${config.bgClass} ${config.textClass} border-transparent hover:scale-[1.02] hover:shadow-lg ${config.hoverClass}`
        }
      `}
      onClick={onClick}
    >
      {/* Background Pattern */}
      <div className={`absolute inset-0 opacity-30 ${config.gradientClass}`} />

      {/* Glow Effect for Active State */}
      {isActive && (
        <div
          className={`absolute -inset-1 ${config.activeBgClass} rounded-2xl blur opacity-20 group-hover:opacity-30 transition-opacity duration-300`}
        />
      )}

      {/* Active Indicator - Enhanced */}
      {isActive && (
        <div className="absolute top-3 right-3 z-10">
          <div className="bg-white/90 backdrop-blur-sm rounded-full p-1 shadow-lg">
            <Check size={14} className="text-current font-bold" />
          </div>
        </div>
      )}

      {/* Content */}
      <div className="relative z-10 flex items-center gap-3 h-full">
        {/* Icon Container */}
        <div
          className={`
          w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-300
          ${isActive ? "bg-white/20 backdrop-blur-sm" : "bg-white/60 group-hover:bg-white/80 group-hover:scale-110"}
        `}
        >
          <IconComponent
            size={20}
            className={`transition-all duration-300 ${isActive ? "text-current" : "text-current"}`}
          />
        </div>

        {/* Text Content */}
        <div className="flex-1 min-w-0">
          <h3
            className={`
            font-semibold text-sm leading-tight transition-all duration-300
            ${isActive ? "text-current" : "text-current group-hover:scale-105"}
          `}
          >
            {sceneName}
          </h3>

          {/* Subtitle for active state */}
          {isActive && <p className="text-xs mt-1 opacity-90 animate-fade-in">Aktive Szene</p>}
        </div>
      </div>

      {/* Hover shine effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 transform -skew-x-12 group-hover:animate-shimmer" />
    </div>
  );
};

export default LightSceneCard;
