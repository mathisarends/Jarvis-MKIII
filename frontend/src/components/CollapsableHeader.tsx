import React from "react";
import { ChevronUp } from "lucide-react";

interface CollapsibleHeaderProps {
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
}

export const CollapsibleHeader: React.FC<CollapsibleHeaderProps> = ({
  title,
  isExpanded,
  onToggle,
  className = "",
}) => {
  return (
    <div
      className={`flex items-center justify-between cursor-pointer mb-3 p-2 pr-6 -m-2 rounded-lg hover:bg-gray-50 transition-colors duration-200 ${className}`}
      onClick={onToggle}
    >
      <h3 className="text-lg font-medium text-gray-700">{title}</h3>

      <button
        className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 transition-all duration-200"
        aria-label={isExpanded ? "Collapse" : "Expand"}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={`transform transition-transform duration-300 ${isExpanded ? "rotate-0" : "rotate-180"}`}>
          <ChevronUp size={18} />
        </div>
      </button>
    </div>
  );
};

export default CollapsibleHeader;
