import React, { useState, useEffect } from "react";
import { CloudMoon } from "lucide-react";

interface SleepScheduleItemProps {
  time: string;
  timeFromNow: string;
  isEnabled: boolean;
  onToggle: () => void;
}

const SleepScheduleItem: React.FC<SleepScheduleItemProps> = ({ time, isEnabled, onToggle }) => {
  const [timeFromNow, setTimeFromNow] = useState<string>("");

  useEffect(() => {
    const calculateTimeFromNow = () => {
      const now = new Date();

      const [hours, minutes] = time.split(":").map(Number);

      const targetTime = new Date();
      targetTime.setHours(hours, minutes, 0, 0);

      if (targetTime <= now) {
        targetTime.setDate(targetTime.getDate() + 1);
      }

      const diffMs = targetTime.getTime() - now.getTime();

      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

      return `${diffHours}h ${diffMinutes}m from now`;
    };

    setTimeFromNow(calculateTimeFromNow());

    const intervalId = setInterval(() => {
      setTimeFromNow(calculateTimeFromNow());
    }, 60000);

    return () => clearInterval(intervalId);
  }, [time]);

  return (
    <div className="bg-white rounded-lg shadow-sm p-4 flex items-center justify-between max-w-md w-full shadow">
      {/* Linke Seite mit Moon Icon */}
      <div className="flex items-center space-x-5">
        <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
          <CloudMoon className="w-6 h-6 text-gray-500" />
        </div>

        {/* Zeit und Text */}
        <div>
          <div className="text-xl md:text-2xl font-bold text-gray-800">{time}</div>
          <div className="text-sm text-gray-500">{timeFromNow}</div>
        </div>
      </div>

      {/* Verbesserter Toggle-Switch mit mehr Padding */}
      <div
        className={`w-14 h-7 flex items-center rounded-full p-[3px] cursor-pointer transition-all duration-300 ease-in-out ${
          isEnabled ? "bg-blue-500 justify-end" : "bg-gray-300 justify-start"
        }`}
        onClick={onToggle}
      >
        <div className="bg-white w-6 h-6 rounded-full shadow-md transform transition-transform duration-300 ease-in-out hover:scale-105 active:scale-95"></div>
      </div>
    </div>
  );
};

export default SleepScheduleItem;
