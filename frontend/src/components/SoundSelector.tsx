import React, { useState } from "react";
import { ChevronUp } from "lucide-react";
import { useSoundPlayback } from "../contexts/soundPlaybackContext";
import SoundOption, { type Sound } from "./soundOption";

interface SoundSelectorProps {
  title: string;
  sounds: Sound[];
  selectedSound: string;
  onSoundChange: (soundId: string) => void;
}

export const SoundSelector: React.FC<SoundSelectorProps> = ({ title, sounds, selectedSound, onSoundChange }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const { stopAllSounds } = useSoundPlayback();

  const handleToggle = async () => {
    if (isExpanded) {
      await stopAllSounds();
    }
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="w-full">
      {/* Header */}
      <div
        className="flex items-center justify-between cursor-pointer mb-3 p-2 -m-2 rounded-lg hover:bg-gray-50 transition-colors duration-200"
        onClick={handleToggle}
      >
        <h3 className="text-lg font-medium text-gray-700">{title}</h3>

        <button
          className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 transition-all duration-200"
          aria-label={isExpanded ? "Collapse" : "Expand"}
        >
          <div className={`transform transition-transform duration-300 ${isExpanded ? "rotate-0" : "rotate-180"}`}>
            <ChevronUp size={18} />
          </div>
        </button>
      </div>

      {/* Content */}
      <div
        className={`
          space-y-2 overflow-hidden transition-all duration-300 ease-in-out
          ${isExpanded ? "max-h-screen opacity-100" : "max-h-0 opacity-0"}
        `}
      >
        {sounds.map((sound) => (
          <SoundOption
            key={sound.id}
            sound={sound}
            isSelected={selectedSound === sound.id}
            onSelect={() => onSoundChange(sound.id)}
          />
        ))}
      </div>
    </div>
  );
};

export default SoundSelector;
