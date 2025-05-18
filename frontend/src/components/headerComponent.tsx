import React from "react";
import { ChevronLeft } from "lucide-react";

interface HeaderProps {
  title?: string;
  onBackClick?: () => void;
}

const Header: React.FC<HeaderProps> = ({ title = "Sleep Tracker", onBackClick = () => {} }) => {
  return (
    <header className="fixed top-0 left-0 right-0 w-full bg-white py-4 px-5 flex items-center z-30">
      <div className="mr-3">
        <button
          onClick={onBackClick}
          className="w-9 h-9 bg-gray-100 rounded-full grid place-items-center text-gray-500 hover:text-gray-700 hover:bg-gray-200 transition-colors"
        >
          <ChevronLeft size={22} />
        </button>
      </div>

      <h1 className="text-2xl text-gray-800">{title}</h1>
    </header>
  );
};

export default Header;
