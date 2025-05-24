import React from "react";
import { useSoundPlayback } from "../contexts/soundPlaybackContext";
import SoundOption, { type Sound } from "./SoundOption";
import CollapsibleSection from "./CollapsableSection";

interface SoundSelectorProps {
  title: string;
  sounds: Sound[];
  selectedSound: string;
  onSoundChange: (soundId: string) => void;
}

export const SoundSelector: React.FC<SoundSelectorProps> = ({ title, sounds, selectedSound, onSoundChange }) => {
  const { stopAllSounds } = useSoundPlayback();

  // Callback when section gets collapsed
  const handleCollapse = async (isExpanded: boolean) => {
    if (!isExpanded) {
      await stopAllSounds();
    }
  };

  return (
    <CollapsibleSection title={title} defaultExpanded={true} onToggle={handleCollapse}>
      {sounds.map((sound) => (
        <SoundOption
          key={sound.id}
          sound={sound}
          isSelected={selectedSound === sound.id}
          onSelect={() => onSoundChange(sound.id)}
        />
      ))}
    </CollapsibleSection>
  );
};

export default SoundSelector;
