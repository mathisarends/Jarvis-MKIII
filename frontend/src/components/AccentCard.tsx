import React from "react";

interface AccentCardProps {
  children: React.ReactNode;
  isActive?: boolean;
  onClick?: () => void;
  className?: string;
}

export const AccentCard: React.FC<AccentCardProps> = ({ children, isActive = false, onClick, className = "" }) => {
  const borderClass = isActive ? "border-l-teal-500" : "border-l-transparent";

  return (
    <div
      className={`
        bg-white rounded-lg overflow-hidden
        border-l-4 transition-all duration-200 ${className}
        ${borderClass}
      `}
      onClick={onClick}
    >
      <div className="px-4 py-3">{children}</div>
    </div>
  );
};

export default AccentCard;
