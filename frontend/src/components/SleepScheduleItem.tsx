import React, { useState, useEffect } from "react";
import { CloudMoon, Bell } from "lucide-react";

interface SleepScheduleItemProps {
  time: string;
  isEnabled: boolean;
  onToggle: () => void;
  onDelete?: () => void;
}

const SleepScheduleItem: React.FC<SleepScheduleItemProps> = ({ time, isEnabled, onToggle, onDelete }) => {
  const [timeFromNow, setTimeFromNow] = useState<string>("");
  const [isHovered, setIsHovered] = useState(false);

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

  // Determine if it's a night alarm (between 20:00 and 6:00)
  const isNightAlarm = () => {
    const [hours] = time.split(":").map(Number);
    return hours >= 20 || hours < 6;
  };

  return (
    <div
      className={`bg-white rounded-lg shadow-md transition-all duration-300 hover:shadow-lg 
                ${isEnabled ? "border-l-4 border-l-teal-300" : ""}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="p-5">
        {/* Top section with time and switch */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center
                          ${isNightAlarm() ? "bg-indigo-100 text-indigo-600" : "bg-amber-100 text-amber-600"}`}
            >
              {isNightAlarm() ? <CloudMoon className="w-5 h-5" /> : <Bell className="w-5 h-5" />}
            </div>
            <div className="text-2xl font-bold text-gray-800">{time}</div>
          </div>

          {/* Modern Toggle Switch in Teal */}
          <div
            className={`w-12 h-6 flex items-center rounded-full p-[2px] cursor-pointer transition-all duration-300
                      ${isEnabled ? "bg-teal-300" : "bg-gray-300"}`}
            onClick={onToggle}
          >
            <div
              className={`bg-white w-5 h-5 rounded-full shadow-md transform transition-transform duration-300
                        ${isEnabled ? "translate-x-6" : "translate-x-0"}`}
            ></div>
          </div>
        </div>

        {/* Bottom section with timeFromNow */}
        <div className="flex justify-between items-center">
          <div className="text-sm text-gray-500 font-medium">{timeFromNow}</div>

          {/* Delete button appears on hover */}
          {onDelete && (
            <button
              onClick={onDelete}
              className={`text-gray-400 hover:text-red-500 transition-opacity duration-300
                        ${isHovered ? "opacity-100" : "opacity-0"}`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Status indicator at bottom in Teal */}
      <div className="px-5 py-2 border-t border-gray-100 text-xs font-medium ext-gray-500 bg-gray-50">
        {isEnabled ? "Active" : "Inactive"}
      </div>
    </div>
  );
};

export default SleepScheduleItem;
