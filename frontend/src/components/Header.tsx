import React from "react";
import { ChevronLeft, User } from "lucide-react";

// Vereinfachte Header Props
interface HeaderProps {
  title?: string;
  onBackClick?: () => void;
  profilePicture?: string;
}

const Header: React.FC<HeaderProps> = ({ title = "", onBackClick, profilePicture }) => {
  return (
    <header className="fixed top-0 left-0 right-0 flex justify-between items-center h-16 px-[7.5%] bg-white shadow-sm backdrop-blur-sm z-50 md:h-16 sm:px-[5%] sm:h-[3.4rem]">
      <div className="flex items-center">
        {onBackClick && (
          <button
            onClick={onBackClick}
            className="w-9 h-9 bg-gray-100 rounded-full grid place-items-center text-gray-500 hover:text-gray-700 hover:bg-gray-200 transition-colors"
          >
            <ChevronLeft size={22} />
          </button>
        )}

        <div className="ml-4 flex items-center text-2xl">
          <h1 className="font-medium text-gray-800">{title}</h1>
        </div>
      </div>

      <div className="flex items-center shadow-xl border rounded-full">
        <div className="relative w-9 h-9 rounded-full overflow-hidden cursor-pointer group">
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10"></div>

          {profilePicture ? (
            <img src={profilePicture} alt="Profile" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full bg-gray-100 grid place-items-center text-gray-500">
              <User size={20} />
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
