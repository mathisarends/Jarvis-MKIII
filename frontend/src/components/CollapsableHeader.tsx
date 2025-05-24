import React from "react";
import { ExpandButton } from "./ExpandCircleIcon";

interface CollapsibleHeaderProps {
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
}

export const CollapsibleHeader: React.FC<CollapsibleHeaderProps> = ({ title, isExpanded, onToggle }) => {
  return (
    <div
      className="flex items-center justify-between cursor-pointer mb-3 p-2 pr-6 -m-2 rounded-lg hover:bg-gray-50 transition-colors duration-200 group"
      onClick={onToggle}
    >
      <h3 className="text-lg font-medium text-gray-700 select-none">{title}</h3>

      <ExpandButton
        isExpanded={isExpanded}
        onClick={(e) => {
          e?.stopPropagation();
        }}
      />
    </div>
  );
};

export default CollapsibleHeader;
