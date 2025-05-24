import React from "react";
import { ChevronUp } from "lucide-react";
import CircleIconButton from "./CircleIconButton";

interface ExpandButtonProps {
  isExpanded: boolean;
  onClick: (e?: React.MouseEvent) => void;
}

export const ExpandButton: React.FC<ExpandButtonProps> = ({ isExpanded, onClick }) => {
  // Animiertes ChevronUp Icon als Komponente
  const AnimatedChevronUp = ({ size = 22 }) => (
    <div className={`transform transition-transform duration-300 ${isExpanded ? "rotate-0" : "rotate-180"}`}>
      <ChevronUp size={size} />
    </div>
  );

  return <CircleIconButton icon={AnimatedChevronUp} onClick={onClick} />;
};
