import React, { useState, useRef } from "react";
import { CloudMoon, Bell, Trash2 } from "lucide-react";
import CircleIconButton from "./CircleIconButton";

interface SleepScheduleItemProps {
  time: string;
  isEnabled: boolean;
  onToggle: () => void;
  onDelete?: () => void;
  timeUntil?: string | null;
  scheduled?: boolean;
  nextExecution?: string | null;
}

const SleepScheduleItem: React.FC<SleepScheduleItemProps> = ({
  time,
  isEnabled,
  onToggle,
  onDelete,
  timeUntil,
  scheduled,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const itemRef = useRef<HTMLDivElement>(null);

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

  const getStatusText = () => {
    if (!isEnabled) {
      return "Inactive";
    }
    if (scheduled === false) {
      return "Not scheduled";
    }
    return "Active";
  };

  const getBorderColor = () => {
    if (!isEnabled) {
      return "border-l-gray-300";
    }
    if (scheduled === false) {
      return "border-l-orange-300";
    }
    return "border-l-teal-300";
  };

  const getTimeDisplay = () => {
    if (!isEnabled) {
      return "Inactive";
    }
    if (timeUntil) {
      return `${timeUntil} from now`;
    }
    return "Active";
  };

  return (
    <div
      ref={itemRef}
      className={`bg-white rounded-lg shadow-md transition-all duration-300 hover:shadow-lg 
                ${getBorderColor()} border-l-4
                ${isDeleting ? "deleting" : ""}
                relative overflow-hidden`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="p-5">
        {/* Top section with time and switch */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
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

        {/* Bottom section with time display */}
        <div className="flex justify-between items-center">
          <div className="text-sm text-gray-500 font-medium">{getTimeDisplay()}</div>

          {/* Delete button appears on hover */}
          {onDelete && (
            <div className={`transition-opacity duration-300 ${isHovered ? "opacity-100" : "opacity-0"}`}>
              <CircleIconButton icon={Trash2} onClick={handleDelete} />
            </div>
          )}
        </div>
      </div>

      {/* Status indicator at bottom */}
      <div className="px-5 py-2 border-t border-gray-100 text-xs font-medium text-gray-500 bg-gray-50">
        {getStatusText()}
      </div>
    </div>
  );
};

export default SleepScheduleItem;
