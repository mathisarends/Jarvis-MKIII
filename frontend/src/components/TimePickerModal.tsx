import React, { useState, useEffect } from "react";
import { X, Clock } from "lucide-react";
import CircleIconButton from "./CircleIconButton";

// Time Picker Modal Component
const TimePickerModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSave: (time: string) => void;
}> = ({ isOpen, onClose, onSave }) => {
  const [hours, setHours] = useState("12");
  const [minutes, setMinutes] = useState("25");

  const hourOptions = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, "0"));

  const minuteOptions = Array.from({ length: 12 }, (_, i) => (i * 5).toString().padStart(2, "0"));

  const handleSave = () => {
    onSave(`${hours}:${minutes}`);
    onClose();
  };

  // Prevent body scrolling when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "auto";
    }
    return () => {
      document.body.style.overflow = "auto";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose}></div>

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-xl max-w-md w-[90%] overflow-hidden">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Einstellungen</h2>
          <CircleIconButton onClick={onClose} icon={X} />
        </div>

        {/* Time Selection */}
        <div className="p-6">
          <div className="flex justify-center items-center space-x-4">
            {/* Hours */}
            <div className="relative">
              <label className="block text-sm font-medium text-gray-500 mb-1 text-center">Hours</label>
              <select
                value={hours}
                onChange={(e) => setHours(e.target.value)}
                className="hide-scrollbar appearance-none bg-gray-100 text-gray-900 text-center text-2xl py-3 px-4 rounded-lg w-24 focus:outline-none focus:ring-2 focus:ring-teal-500"
              >
                {hourOptions.map((hour) => (
                  <option key={hour} value={hour}>
                    {hour}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 mt-5 text-gray-700">
                <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                  <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
                </svg>
              </div>
            </div>

            <div className="text-3xl font-light text-gray-500 mt-6">:</div>

            {/* Minutes */}
            <div className="relative">
              <label className="block text-sm font-medium text-gray-500 mb-1 text-center">Minutes</label>
              <select
                value={minutes}
                onChange={(e) => setMinutes(e.target.value)}
                className="hide-scrollbar appearance-none bg-gray-100 text-gray-900 text-center text-2xl py-3 px-4 rounded-lg w-24 focus:outline-none focus:ring-2 focus:ring-teal-500 border border-teal-400"
              >
                {minuteOptions.map((minute) => (
                  <option key={minute} value={minute}>
                    {minute}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 mt-5 text-gray-700">
                <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                  <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
                </svg>
              </div>
            </div>
          </div>

          {/* Clock visual */}
          <div className="flex justify-center mt-6">
            <div className="relative w-36 h-36 rounded-full border-4 border-gray-200">
              <div className="absolute inset-0 flex justify-center">
                <div
                  className="w-1 bg-teal-500"
                  style={{
                    height: "30%",
                    transformOrigin: "bottom",
                    transform: `rotate(${(parseInt(hours) % 12) * 30 + parseInt(minutes) / 2}deg)`,
                    marginTop: "20%",
                  }}
                ></div>
              </div>
              <div className="absolute inset-0 flex justify-center">
                <div
                  className="w-1 bg-teal-400"
                  style={{
                    height: "40%",
                    transformOrigin: "bottom",
                    transform: `rotate(${parseInt(minutes) * 6}deg)`,
                    marginTop: "10%",
                  }}
                ></div>
              </div>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-3 h-3 rounded-full bg-teal-500"></div>
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end p-4 space-x-2 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Abbrechen
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-teal-500 text-white rounded-lg shadow-md hover:bg-teal-600 transition-colors"
          >
            Erstellen
          </button>
        </div>
      </div>
    </div>
  );
};

export default TimePickerModal;
