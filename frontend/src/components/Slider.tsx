import React, { useState, useRef } from "react";
import { Volume2, Sun } from "lucide-react";

interface SliderProps {
  value: number;
  onChange: (value: number) => void;
  onChangeEnd?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  icon: React.ReactNode;
  label: string;
  valueLabel?: string;
}

const Slider: React.FC<SliderProps> = ({
  value,
  onChange,
  onChangeEnd,
  min = 0,
  max = 100,
  step = 1,
  icon,
  label,
  valueLabel,
}) => {
  const percentage = ((value - min) / (max - min)) * 100;
  const isDragging = useRef(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = Number(e.target.value);
    onChange(newValue); // ✅ Für visuelle Updates während dem Ziehen
  };

  const handlePointerDown = () => {
    isDragging.current = true;
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLInputElement>) => {
    if (isDragging.current) {
      isDragging.current = false;
      const newValue = Number((e.target as HTMLInputElement).value);
      onChangeEnd?.(newValue); // ✅ Nur beim Loslassen
    }
  };

  // Fallback für ältere Browser / Touch
  const handleMouseUp = (e: React.MouseEvent<HTMLInputElement>) => {
    if (isDragging.current) {
      isDragging.current = false;
      const newValue = Number((e.target as HTMLInputElement).value);
      onChangeEnd?.(newValue);
    }
  };

  const handleTouchEnd = (e: React.TouchEvent<HTMLInputElement>) => {
    if (isDragging.current) {
      isDragging.current = false;
      const newValue = Number((e.target as HTMLInputElement).value);
      onChangeEnd?.(newValue);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border-l-4 border-l-teal-500 overflow-hidden">
      <div className="px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-100">{icon}</div>
            <div>
              <div className="font-medium text-gray-800">{label}</div>
              <div className="text-xs text-gray-500">{valueLabel || `${value}${max <= 1 ? "" : "%"}`}</div>
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
              onChange={handleChange}
              onPointerDown={handlePointerDown}
              onPointerUp={handlePointerUp}
              onMouseUp={handleMouseUp}
              onTouchEnd={handleTouchEnd}
              className="absolute top-0 left-0 w-full h-full opacity-0 cursor-pointer"
            />
          </div>
          <div className="flex justify-between mt-1 text-xs text-gray-500">
            <span>{min}</span>
            <span>{max}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

interface BrightnessSliderProps {
  min?: number;
  max?: number;
  defaultValue?: number;
  value?: number;
  onChange?: (value: number) => void;
  onChangeEnd?: (value: number) => void;
}

export const BrightnessSlider: React.FC<BrightnessSliderProps> = ({
  min = 0,
  max = 100,
  defaultValue = 70,
  value: controlledValue,
  onChange: controlledOnChange,
  onChangeEnd: controlledOnChangeEnd,
}) => {
  const [internalBrightness, setInternalBrightness] = useState(defaultValue);

  // Use controlled value if provided, otherwise use internal state
  const brightness = controlledValue !== undefined ? controlledValue : internalBrightness;
  const handleChange = controlledOnChange || setInternalBrightness;

  const getBrightnessLabel = (val: number) => {
    const percentage = ((val - min) / (max - min)) * 100;
    if (percentage > 80) return "Bright";
    if (percentage > 40) return "Medium";
    return "Dim";
  };

  const handleChangeEnd = (value: number) => {
    console.log(`🔆 Brightness changed to: ${value}`);
    controlledOnChangeEnd?.(value);
  };

  return (
    <Slider
      value={brightness}
      onChange={handleChange}
      onChangeEnd={handleChangeEnd}
      min={min}
      max={max}
      step={max <= 1 ? 0.01 : 1}
      icon={<Sun className="w-4 h-4 text-gray-600" />}
      label="Lamp Brightness"
      valueLabel={getBrightnessLabel(brightness)}
    />
  );
};

// Volume Slider Component Props
interface VolumeSliderProps {
  min?: number;
  max?: number;
  defaultValue?: number;
  value?: number;
  onChange?: (value: number) => void;
  onChangeEnd?: (value: number) => void;
}

export const VolumeSlider: React.FC<VolumeSliderProps> = ({
  min = 0,
  max = 100,
  defaultValue = 50,
  value: controlledValue,
  onChange: controlledOnChange,
  onChangeEnd: controlledOnChangeEnd,
}) => {
  const [internalVolume, setInternalVolume] = useState(defaultValue);

  const volume = controlledValue !== undefined ? controlledValue : internalVolume;
  const handleChange = controlledOnChange || setInternalVolume;

  const getVolumeLabel = (vol: number) => {
    if (vol === min) return "Mute";
    const percentage = ((vol - min) / (max - min)) * 100;
    if (percentage < 30) return "Quiet";
    if (percentage < 70) return "Medium";
    return "Loud";
  };

  const handleChangeEnd = (value: number) => {
    console.log(`🔊 Volume changed to: ${value}`);
    controlledOnChangeEnd?.(value);
  };

  return (
    <Slider
      value={volume}
      onChange={handleChange}
      onChangeEnd={handleChangeEnd}
      min={min}
      max={max}
      step={max <= 1 ? 0.01 : 1}
      icon={<Volume2 className="w-4 h-4 text-gray-600" />}
      label="Alarm Volume"
      valueLabel={getVolumeLabel(volume)}
    />
  );
};
