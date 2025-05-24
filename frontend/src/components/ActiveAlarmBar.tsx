import React, { useState, useEffect } from "react";
import { Square } from "lucide-react";

interface ActiveAlarmBarProps {
  totalDuration: number; // in seconds (e.g., 540 for 9 minutes)
  onStop: () => void;
}

const ALARM_LABEL = "Alarm";

const ActiveAlarmBar: React.FC<ActiveAlarmBarProps> = ({ totalDuration, onStop }) => {
  const [remainingTime, setRemainingTime] = useState(totalDuration);

  // Countdown timer
  useEffect(() => {
    const interval = setInterval(() => {
      setRemainingTime((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Format time as MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
          <span className="text-lg font-medium text-orange-900">{ALARM_LABEL} läuft</span>
          <span className="text-md font-mono text-orange-800 bg-orange-100 px-2 py-1 rounded">
            {formatTime(remainingTime)}
          </span>
        </div>

        <button
          onClick={onStop}
          className="flex items-center gap-2 px-3 py-1 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600 transition-colors hover:scale-95 transition duration-200"
        >
          <Square className="w-3 h-3 fill-current" />
          Stopp
        </button>
      </div>
    </div>
  );
};

export default ActiveAlarmBar;
