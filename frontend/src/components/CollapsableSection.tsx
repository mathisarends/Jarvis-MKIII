import React, { useState } from "react";
import { ExpandButton } from "./ExpandCircleIcon";

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  onToggle?: (isExpanded: boolean) => void;
}

export const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  children,
  defaultExpanded = true,
  onToggle,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const handleToggle = () => {
    const newState = !isExpanded;
    setIsExpanded(newState);
    onToggle?.(newState);
  };

  return (
    <div className={`w-full`}>
      {/* Header */}
      <div
        className="flex items-center justify-between cursor-pointer mb-3 p-2 pr-6 -m-2 rounded-lg hover:bg-gray-50 transition-colors duration-200 group"
        onClick={handleToggle}
      >
        <h3 className="text-lg font-medium text-gray-700 select-none">{title}</h3>

        <ExpandButton
          isExpanded={isExpanded}
          onClick={(e) => {
            e?.stopPropagation();
          }}
        />
      </div>

      {/* Collapsible Content */}
      <div
        className={`
          overflow-hidden transition-all duration-300 ease-in-out
          ${isExpanded ? "max-h-screen opacity-100" : "max-h-0 opacity-0"}
        `}
      >
        {/* Content wrapper with consistent spacing */}
        <div className="space-y-2">{children}</div>
      </div>
    </div>
  );
};

export default CollapsibleSection;
