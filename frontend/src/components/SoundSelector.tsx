import React, { useState, useRef } from "react";
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

interface SoundOptionProps {
  soundName: string;
  soundFile: string;
  isSelected: boolean;
  onSelect: () => void;
  category: "wake-up" | "get-up";
}

const SoundOption: React.FC<SoundOptionProps> = ({ soundName, soundFile, isSelected, onSelect, category }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Get the display name from the file name
  const getDisplayName = () => {
    const baseName = soundName.replace(`${category}-`, "").replace(".mp3", "");
    return baseName
      .split("-")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  // Get the appropriate icon based on the sound name
  const getIcon = () => {
    const name = soundName.toLowerCase();

    // Map sound names to appropriate icons
    if (name.includes("blossom") || name.includes("cherry")) return <Leaf size={18} />;
    if (name.includes("retreat")) return <Sun size={18} />;
    if (name.includes("wave")) return <Waves size={18} />;
    if (name.includes("wisdom") || name.includes("temple")) return <Bell size={18} />;
    if (name.includes("time") || name.includes("clock")) return <Clock size={18} />;
    if (name.includes("aurora") || name.includes("galaxy")) return <Moon size={18} />;
    if (name.includes("shimmer")) return <Sunrise size={18} />;
    if (name.includes("forest") || name.includes("jungle")) return <Wind size={18} />;
    if (name.includes("paradise") || name.includes("serene")) return <Cloud size={18} />;
    if (name.includes("bird") || name.includes("gong")) return <Bird size={18} />;
    if (name.includes("train") || name.includes("focus")) return <Zap size={18} />;

    return <Music size={18} />;
  };

  const togglePlayback = () => {
    if (!audioRef.current) {
      audioRef.current = new Audio(soundFile);
      audioRef.current.onended = () => setIsPlaying(false);
    }

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      // Stop any other playing audio (would need to implement a global audio context for this)
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  return (
    <div
      className={`
      bg-white rounded-lg shadow-sm overflow-hidden
      border-l-4 ${isSelected ? "border-l-teal-500" : "border-l-transparent"} 
      transition-all duration-200
      ${isSelected ? "shadow-md" : "shadow-sm"}
    `}
    >
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-100 text-gray-600">
            {getIcon()}
          </div>
          <span className="font-medium text-gray-800">{getDisplayName()}</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Play/Pause button */}
          <button
            onClick={togglePlayback}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200"
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>

          {/* Selection button */}
          <button
            onClick={onSelect}
            className={`
              w-8 h-8 flex items-center justify-center rounded-full
              ${isSelected ? "bg-teal-500 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}
            `}
          >
            {isSelected ? <Check size={16} /> : null}
          </button>
        </div>
      </div>
    </div>
  );
};

// Example usage component with multiple sound options
export const SoundSelector: React.FC<{
  category: "wake-up" | "get-up";
  title: string;
  sounds: string[];
  selectedSound: string;
  onSoundChange: (sound: string) => void;
}> = ({ category, title, sounds, selectedSound, onSoundChange }) => {
  return (
    <div className="mb-6">
      <h3 className="text-lg font-medium text-gray-700 mb-3">{title}</h3>
      <div className="space-y-2">
        {sounds.map((sound) => (
          <SoundOption
            key={sound}
            soundName={sound}
            soundFile={`/sounds/${category}/${sound}`} // Path to your sound files
            isSelected={selectedSound === sound}
            onSelect={() => onSoundChange(sound)}
            category={category}
          />
        ))}
      </div>
    </div>
  );
};

export default SoundOption;
