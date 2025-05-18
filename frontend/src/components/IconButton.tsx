import React from "react";
import type { LucideIcon } from "lucide-react";

interface CircleIconButtonProps {
  icon: LucideIcon;

  onClick: () => void;
}

const CircleIconButton: React.FC<CircleIconButtonProps> = ({ icon: Icon, onClick }) => {
  return (
    <button
      onClick={onClick}
      className="w-8 h-8 bg-gray-100 rounded-full grid place-items-center text-gray-500 hover:text-gray-700 hover:bg-gray-200 transition-colors"
    >
      <Icon size={22} />
    </button>
  );
};

export default CircleIconButton;
