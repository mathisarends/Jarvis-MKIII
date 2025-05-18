import React, { useState } from "react";
import { Volume2, Sun } from "lucide-react";

interface SliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  icon: React.ReactNode;
  label: string;
  valueLabel?: string;
}

const Slider: React.FC<SliderProps> = ({ value, onChange, min = 0, max = 100, step = 1, icon, label, valueLabel }) => {
  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div className="bg-white rounded-lg shadow-sm border-l-4 border-l-teal-500 overflow-hidden">
      <div className="px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-100">{icon}</div>
            <div>
              <div className="font-medium text-gray-800">{label}</div>
              <div className="text-xs text-gray-500">{valueLabel || `${value}%`}</div>
            </div>
          </div>
        </div>

        <div className="mt-4">
          <div className="relative w-full h-2 bg-gray-200 rounded-full">
            <div
              className="absolute top-0 left-0 h-full bg-teal-500 rounded-full"
              style={{ width: `${percentage}%` }}
            ></div>
            <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={value}
              onChange={(e) => onChange(Number(e.target.value))}
              className="absolute top-0 left-0 w-full h-full opacity-0 cursor-pointer"
            />
          </div>
          <div className="flex justify-between mt-1 text-xs text-gray-500">
            <span>Min</span>
            <span>Max</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Brightness Slider Component
export const BrightnessSlider: React.FC = () => {
  const [brightness, setBrightness] = useState(70); // Default 70%

  return (
    <Slider
      value={brightness}
      onChange={setBrightness}
      icon={<Sun className="w-4 h-4 text-gray-600" />}
      label="Lamp Brightness"
      valueLabel={brightness > 80 ? "Bright" : brightness > 40 ? "Medium" : "Dim"}
    />
  );
};

// Volume Slider Component
export const VolumeSlider: React.FC = () => {
  const [volume, setVolume] = useState(50); // Default 50%

  const getVolumeLabel = (vol: number) => {
    if (vol === 0) return "Mute";
    if (vol < 30) return "Quiet";
    if (vol < 70) return "Medium";
    return "Loud";
  };

  return (
    <Slider
      value={volume}
      onChange={setVolume}
      icon={<Volume2 className="w-4 h-4 text-gray-600" />}
      label="Alarm Volume"
      valueLabel={getVolumeLabel(volume)}
    />
  );
};
