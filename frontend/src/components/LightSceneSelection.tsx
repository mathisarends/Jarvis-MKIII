import React from "react";
import LightSceneCard from "./LightSceneCard";

interface LightSceneSectionProps {
  availableScenes: string[];
  activeScene: string | null;
  onSceneSelect: (sceneName: string) => void;
}

const LightSceneSection: React.FC<LightSceneSectionProps> = ({ availableScenes, activeScene, onSceneSelect }) => {
  if (availableScenes.length === 0) {
    return null;
  }

  return (
    <div className="w-full">
      {/* Header with title and active scene indicator */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-800">Lichtszenen</h3>
        {activeScene && (
          <div className="text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded-full">Aktiv: {activeScene}</div>
        )}
      </div>

      {/* Responsive grid of scene cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {availableScenes.map((sceneName) => (
          <LightSceneCard
            key={sceneName}
            sceneName={sceneName}
            isActive={activeScene === sceneName}
            onClick={() => onSceneSelect(sceneName)}
          />
        ))}
      </div>
    </div>
  );
};

export default LightSceneSection;
