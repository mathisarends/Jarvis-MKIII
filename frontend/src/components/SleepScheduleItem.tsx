import React, { useState, useEffect, useRef } from "react";
import { CloudMoon, Bell, Trash2, AlertTriangle, Check, X } from "lucide-react";
import CircleIconButton from "./CircleIconButton";

interface SleepScheduleItemProps {
  time: string;
  isEnabled: boolean;
  onToggle: () => void;
  onDelete?: () => void;
}

const SleepScheduleItem: React.FC<SleepScheduleItemProps> = ({ time, isEnabled, onToggle, onDelete }) => {
  const [timeFromNow, setTimeFromNow] = useState<string>("");
  const [isHovered, setIsHovered] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const itemRef = useRef<HTMLDivElement>(null);

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

  const handleDelete = () => {
    if (!onDelete) {
      return;
    }

    setIsDeleting(true);

    setTimeout(() => {
      onDelete();
    }, 500);
  };

  const isNightAlarm = () => {
    const [hours] = time.split(":").map(Number);
    return hours >= 20 || hours < 6;
  };

  return (
    <div
      ref={itemRef}
      className={`bg-white rounded-lg shadow-md transition-all duration-300 hover:shadow-lg 
                ${isEnabled ? "border-l-4 border-l-teal-300" : "border-l-4 border-1-gray-300"}
                ${isDeleting ? "deleting" : ""}
                relative overflow-hidden`}
      onMouseEnter={() => setIsHovered(true)}
    >
      <div className="p-5">
        {/* Top section with time and switch */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            {/* Original icon display with color styling */}
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center
                          ${isNightAlarm() ? "bg-indigo-100 text-indigo-400" : "bg-amber-100 text-amber-500"}`}
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
            <div className={`transition-opacity duration-300 ${isHovered ? "opacity-100" : "opacity-0"}`}>
              <CircleIconButton icon={Trash2} onClick={handleDelete} />
            </div>
          )}
        </div>
      </div>

      {/* Status indicator at bottom in Teal */}
      <div className="px-5 py-2 border-t border-gray-100 text-xs font-medium text-gray-500 bg-gray-50">
        {isEnabled ? "Active" : "Inactive"}
      </div>
    </div>
  );
};

export default SleepScheduleItem;
