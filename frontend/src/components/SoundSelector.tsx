import React, { useState } from "react";
import { useSoundPlayback } from "../contexts/soundPlaybackContext";
import SoundOption, { type Sound } from "./soundOption";
import CollapsibleHeader from "./CollapsableHeader";

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
      <CollapsibleHeader title={title} isExpanded={isExpanded} onToggle={handleToggle} />

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
