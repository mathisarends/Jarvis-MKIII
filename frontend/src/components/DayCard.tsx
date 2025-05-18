import React from "react";

interface DayCardProps {
  day: string;
  date: number;
  isSelected: boolean;
  onClick: () => void;
}

const DayCard: React.FC<DayCardProps> = ({ day, date, isSelected, onClick }) => {
  return (
    <div
      className={
        `flex flex-col items-center justify-center w-12 h-16 select-none cursor-pointer 
         transition-all duration-200 border-b-2 rounded-none ` +
        (isSelected
          ? "border-teal-500 bg-teal-50 text-teal-700 shadow-sm"
          : "border-transparent bg-gray-100 text-gray-700 hover:border-teal-200")
      }
      onClick={onClick}
    >
      <span className="text-xs font-medium">{day}</span>
      <span className="text-lg font-bold">{date}</span>
    </div>
  );
};

export default DayCard;
