import React, { useState } from "react";
import { Wifi, Headphones, ChevronDown } from "lucide-react";
import type { AudioSystem } from "../api/audioSystemModels";

interface AudioSystemSelectorProps {
  systems: AudioSystem[];
  onSystemChange: (systemId: string) => void;
}

export const AudioSystemSelector: React.FC<AudioSystemSelectorProps> = ({ systems, onSystemChange }) => {
  const [switching, setSwitching] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const getIcon = (systemId: string) => {
    switch (systemId) {
      case "sonos_era_100":
        return <Wifi className="w-4 h-4" />;
      case "usb_speaker":
        return <Headphones className="w-4 h-4" />;
      default:
        return <Headphones className="w-4 h-4" />;
    }
  };

  const handleSystemChange = async (systemId: string) => {
    if (switching) return;

    setSwitching(systemId);
    setIsOpen(false);
    try {
      await onSystemChange(systemId);
    } finally {
      setSwitching(null);
    }
  };

  const activeSystem = systems.find((system) => system.active);
  const inactiveSystem = systems.find((system) => !system.active);

  return (
    <div className="relative">
      {/* Dropdown Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={switching !== null}
        className="flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg 
                 hover:bg-gray-100 transition-colors disabled:opacity-50 min-w-[160px]"
      >
        {switching ? (
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
        ) : (
          activeSystem && getIcon(activeSystem.id)
        )}

        <span className="text-sm font-medium flex-1 text-left">
          {switching ? "Wechsle..." : activeSystem?.name || "Unbekannt"}
        </span>

        {!switching && <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />}
      </button>

      {/* Dropdown Menu */}
      {isOpen && inactiveSystem && (
        <div
          className="absolute top-full left-0 mt-1 w-full bg-white border border-gray-200 
                      rounded-lg shadow-lg z-50"
        >
          <button
            onClick={() => handleSystemChange(inactiveSystem.id)}
            className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-50 
                     rounded-lg transition-colors"
          >
            <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
              {getIcon(inactiveSystem.id)}
            </div>
            <div className="flex-1">
              <div className="font-medium text-gray-800 text-sm">{inactiveSystem.name}</div>
            </div>
          </button>
        </div>
      )}

      {/* Click outside to close */}
      {isOpen && <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />}
    </div>
  );
};
