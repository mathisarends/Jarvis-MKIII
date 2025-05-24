import React, { useState } from "react";
import { Wifi, Headphones, Radio } from "lucide-react";
import AccentCard from "./AccentCard";
import type { AudioSystem } from "../api/audioSystemModels";
import { defaultEasing } from "framer-motion";
import { ExpandButton } from "./ExpandCircleIcon";

interface AudioSystemSelectorProps {
  systems: AudioSystem[];
  onSystemChange: (systemId: string) => void;
}

interface AudioSystemSelectorProps {
  systems: AudioSystem[];
  onSystemChange: (systemId: string) => void;
}

export const AudioSystemSelector: React.FC<AudioSystemSelectorProps> = ({ systems, onSystemChange }) => {
  const [switching, setSwitching] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  // Simplified system info
  const getSystemInfo = (systemId: string) => {
    switch (systemId) {
      case "sonos_era_100":
        return {
          icon: <Wifi className="w-4 h-4" />,
          color: "text-blue-600",
          bgColor: "bg-blue-100",
        };
      case "usb_speaker":
        return {
          icon: <Headphones className="w-4 h-4" />,
          color: "text-green-600",
          bgColor: "bg-green-100",
        };
      default:
        return {
          icon: <Radio className="w-4 h-4" />,
          color: "text-gray-600",
          bgColor: "bg-gray-100",
        };
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
  const inactiveSystems = systems.filter((system) => !system.active);

  const handleToggle = () => {
    if (inactiveSystems.length > 0) {
      setIsOpen(!isOpen);
    }
  };

  return (
    <div className="relative">
      {/* Clickable Audio System Card */}
      <AccentCard isActive={true}>
        <div className="flex items-center gap-3 cursor-pointer" onClick={handleToggle}>
          {/* System Icon */}
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              getSystemInfo(activeSystem?.id || "").bgColor
            }`}
          >
            <div className={getSystemInfo(activeSystem?.id || "").color}>
              {switching === activeSystem?.id ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current" />
              ) : (
                getSystemInfo(activeSystem?.id || "").icon
              )}
            </div>
          </div>

          {/* System Info - Vertical Layout */}
          <div className="flex-1">
            <div className="text-md text-teal-600 font-medium">Aktiv</div>
            <h4 className="font-medium text-gray-900 text-md">{activeSystem?.name || "Unbekannt"}</h4>
          </div>

          {/* Expand Button */}
          {inactiveSystems.length > 0 && (
            <ExpandButton
              isExpanded={isOpen}
              onClick={(e) => {
                e?.stopPropagation();
                handleToggle();
              }}
            />
          )}
        </div>
      </AccentCard>

      {/* Minimal Dropdown */}
      {isOpen && inactiveSystems.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-full z-50">
          <div className="bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
            {inactiveSystems.map((system) => {
              const systemInfo = getSystemInfo(system.id);
              const isSwitching = switching === system.id;

              return (
                <button
                  key={system.id}
                  onClick={() => handleSystemChange(system.id)}
                  disabled={switching !== null}
                  className="w-full flex items-center gap-3 px-3 py-2 hover:bg-gray-50 transition-colors disabled:opacity-50"
                >
                  {/* System Icon */}
                  <div className={`w-6 h-6 rounded flex items-center justify-center ${systemInfo.bgColor}`}>
                    <div className={systemInfo.color}>
                      {isSwitching ? (
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current" />
                      ) : (
                        systemInfo.icon
                      )}
                    </div>
                  </div>

                  {/* System Name */}
                  <span className="text-lg font-medium text-gray-900">{system.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />}
    </div>
  );
};

export default AudioSystemSelector;
