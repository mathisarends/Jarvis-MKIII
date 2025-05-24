import React, { useRef } from "react";
import AccentCard from "./AccentCard";

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
    onChange(newValue);
  };

  const handlePointerDown = () => {
    isDragging.current = true;
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLInputElement>) => {
    if (isDragging.current) {
      isDragging.current = false;
      const newValue = Number((e.target as HTMLInputElement).value);
      onChangeEnd?.(newValue);
    }
  };

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
    <AccentCard isActive={true}>
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
            className="absolute top-0 left-0 h-full rounded-full bg-teal-500"
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
      </div>
    </AccentCard>
  );
};

export default Slider;
