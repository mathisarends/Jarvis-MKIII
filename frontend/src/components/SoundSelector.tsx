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
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface SoundOptionProps {
  soundName: string;
  soundFile: string;
  isSelected: boolean;
  onSelect: () => void;
  category: "wake-up" | "get-up";
  animationDelay: number;
  style?: React.CSSProperties;
}

const SoundOption: React.FC<SoundOptionProps> = ({
  soundName,
  soundFile,
  isSelected,
  onSelect,
  category,
  animationDelay,
  style,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const getDisplayName = () => {
    const baseName = soundName.replace(`${category}-`, "").replace(".mp3", "");
    return baseName
      .split("-")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const getIcon = () => {
    const name = soundName.toLowerCase();

    const matchedIcon = [
      { match: ["blossom", "cherry"], icon: <Leaf size={18} /> },
      { match: ["retreat"], icon: <Sun size={18} /> },
      { match: ["wave"], icon: <Waves size={18} /> },
      { match: ["wisdom", "temple"], icon: <Bell size={18} /> },
      { match: ["time", "clock"], icon: <Clock size={18} /> },
      { match: ["aurora", "galaxy"], icon: <Moon size={18} /> },
      { match: ["shimmer"], icon: <Sunrise size={18} /> },
      { match: ["forest", "jungle"], icon: <Wind size={18} /> },
      { match: ["paradise", "serene"], icon: <Cloud size={18} /> },
      { match: ["bird", "gong"], icon: <Bird size={18} /> },
      { match: ["train", "focus"], icon: <Zap size={18} /> },
    ].find(({ match }) => match.some((term) => name.includes(term)))?.icon;

    // Default icon if no match found
    return matchedIcon || <Music size={18} />;
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
      style={style}
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

// Enhanced SoundSelector with collapsible functionality
export const SoundSelector: React.FC<{
  category: "wake-up" | "get-up";
  title: string;
  sounds: string[];
  selectedSound: string;
  onSoundChange: (sound: string) => void;
}> = ({ category, title, sounds, selectedSound, onSoundChange }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  // Toggle expanded state with animation handling
  const toggleExpanded = () => {
    setIsAnimating(true);
    setIsExpanded(!isExpanded);

    // Reset animating state after animations complete
    setTimeout(() => {
      setIsAnimating(false);
    }, sounds.length * 50 + 300); // Account for staggered animations plus base duration
  };

  return (
    <div>
      {/* Header with title and toggle button */}
      <div className="flex items-center justify-between cursor-pointer mb-3 pr-4" onClick={toggleExpanded}>
        <h3 className="text-lg font-medium text-gray-700">{title}</h3>
        <button
          className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200"
          aria-label={isExpanded ? "Collapse" : "Expand"}
        >
          {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
      </div>

      {/* Container for sounds with a staggered animation */}
      <div
        className={`space-y-2 overflow-hidden transition-all duration-300 ease-in-out ${
          isExpanded ? "max-h-screen opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        {(isExpanded || isAnimating) &&
          sounds.map((sound, index) => {
            // Calculate staggered delay based on index
            const delay = 0.05 * index;

            // Determine animation style based on expanded state
            const animationStyle = {
              animation: isExpanded
                ? `fadeInUp 0.3s ease forwards ${delay}s`
                : `fadeOutDown 0.3s ease forwards ${delay}s`,
              opacity: isExpanded ? 0 : 1,
            };

            return (
              <SoundOption
                key={sound}
                soundName={sound}
                soundFile={`/sounds/${category}/${sound}`}
                isSelected={selectedSound === sound}
                onSelect={() => onSoundChange(sound)}
                category={category}
                animationDelay={delay}
                style={animationStyle}
              />
            );
          })}
      </div>
    </div>
  );
};

export default SoundOption;
