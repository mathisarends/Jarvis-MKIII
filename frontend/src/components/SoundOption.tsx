import React from "react";
import {
  Play,
  Pause,
  Check,
  Music,
  Wind,
  Waves,
  Bird,
  Sunrise,
  Cloud,
  Leaf,
  Bell,
  Sun,
  Moon,
  Zap,
  Clock,
} from "lucide-react";
import { soundApi } from "../api/alarmApi";
import { useSoundPlayback } from "../contexts/soundPlaybackContext";
import AccentCard from "./AccentCard";

export interface Sound {
  id: string;
  label: string;
}

interface SoundOptionProps {
  sound: Sound;
  isSelected: boolean;
  onSelect: () => void;
}

const SoundOption: React.FC<SoundOptionProps> = ({ sound, isSelected, onSelect }) => {
  const { currentlyPlaying, setCurrentlyPlaying, stopAllSounds } = useSoundPlayback();
  const isPlaying = currentlyPlaying === sound.id;

  const getIcon = () => {
    const name = sound.label.toLowerCase();

    const iconMap = [
      { keywords: ["blossom", "cherry"], icon: <Leaf size={18} /> },
      { keywords: ["retreat"], icon: <Sun size={18} /> },
      { keywords: ["wave"], icon: <Waves size={18} /> },
      { keywords: ["wisdom", "temple"], icon: <Bell size={18} /> },
      { keywords: ["time", "clock"], icon: <Clock size={18} /> },
      { keywords: ["aurora", "galaxy"], icon: <Moon size={18} /> },
      { keywords: ["shimmer"], icon: <Sunrise size={18} /> },
      { keywords: ["forest", "jungle"], icon: <Wind size={18} /> },
      { keywords: ["paradise", "serene"], icon: <Cloud size={18} /> },
      { keywords: ["bird", "gong"], icon: <Bird size={18} /> },
      { keywords: ["train", "focus"], icon: <Zap size={18} /> },
    ];

    const match = iconMap.find(({ keywords }) => keywords.some((keyword) => name.includes(keyword)));

    return match?.icon || <Music size={18} />;
  };

  const handlePlayback = async () => {
    try {
      if (isPlaying) {
        await stopAllSounds();
        return;
      }

      if (currentlyPlaying) {
        await stopAllSounds();
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      await soundApi.play(sound.id);
      setCurrentlyPlaying(sound.id);
    } catch (error) {
      console.error("Error playing sound:", error);
      setCurrentlyPlaying(null);
    }
  };

  return (
    <AccentCard isActive={isSelected} accentColor="teal">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-100 text-gray-600">
            {getIcon()}
          </div>
          <span className="font-medium text-gray-800">{sound.label}</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Play/Pause button */}
          <button
            onClick={handlePlayback}
            className={`
              w-8 h-8 flex items-center justify-center rounded-full 
              transition-all duration-200
              ${
                isPlaying
                  ? "bg-teal-100 text-teal-600 hover:bg-teal-200"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }
            `}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>

          {/* Selection button */}
          <button
            onClick={onSelect}
            className={`
              w-8 h-8 flex items-center justify-center rounded-full
              transition-all duration-200
              ${isSelected ? "bg-teal-500 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}
            `}
          >
            {isSelected && <Check size={16} />}
          </button>
        </div>
      </div>
    </AccentCard>
  );
};

export default SoundOption;
