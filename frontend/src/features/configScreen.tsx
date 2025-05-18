import React, { useState } from "react";
import { BrightnessSlider, VolumeSlider } from "../components/Slider";
import { SoundSelector } from "../components/SoundSelector";

const ConfigScreen: React.FC = () => {
  // State for selected sounds
  const [selectedWakeUpSound, setSelectedWakeUpSound] = useState("wake-up-serene.mp3");
  const [selectedGetUpSound, setSelectedGetUpSound] = useState("get-up-blossom.mp3");

  // Mock sound data (you would likely load this from somewhere)
  const wakeUpSounds = [
    "wake-up-bowl.mp3",
    "wake-up-cherry.mp3",
    "wake-up-focus.mp3",
    "wake-up-fountain.mp3",
    "wake-up-galaxy.mp3",
    "wake-up-gong.mp3",
    "wake-up-jungle.mp3",
    "wake-up-forest.mp3",
    "wake-up-paradise.mp3",
    "wake-up-serene.mp3",
    "wake-up-temple.mp3",
    "wake-up-train.mp3",
    "wake-up-waves.mp3",
  ];

  const getUpSounds = [
    "get-up-aurora.mp3",
    "get-up-blossom.mp3",
    "get-up-retreat.mp3",
    "get-up-shake.mp3",
    "get-up-shimmer.mp3",
    "get-up-time.mp3",
    "get-up-wisdom.mp3",
  ];

  return (
    <div className="flex flex-col gap-0">
      {/* Sliders */}
      <div className="space-y-3 mb-8">
        <BrightnessSlider />
        <VolumeSlider />
      </div>

      {/* Sound Selectors */}
      <SoundSelector
        category="wake-up"
        title="Wake Up Sounds"
        sounds={wakeUpSounds}
        selectedSound={selectedWakeUpSound}
        onSoundChange={setSelectedWakeUpSound}
      />

      <div className="border-t border-gray-200 my-6"></div>

      <SoundSelector
        category="get-up"
        title="Get Up Sounds"
        sounds={getUpSounds}
        selectedSound={selectedGetUpSound}
        onSoundChange={setSelectedGetUpSound}
      />
    </div>
  );
};

export default ConfigScreen;
