import React from "react";
import { ChevronLeft, User } from "lucide-react";
import CircleIconButton from "../components/CircleIconButton";
import { useHeader } from "../contexts/headerContext";

interface HeaderProps {
  title?: string;
  onBackClick?: () => void;
  profilePicture?: string;
}

const Header: React.FC<HeaderProps> = ({ title = "", onBackClick, profilePicture = "/images/profile_picture.png" }) => {
  const { config } = useHeader();

  // Render the right element based on the config
  const renderRightElement = () => {
    switch (config.rightElement) {
      case "button":
        if (config.buttonIcon && config.buttonCallback) {
          const ButtonIcon = config.buttonIcon;
          return <CircleIconButton icon={ButtonIcon} onClick={config.buttonCallback} />;
        }
        return null;

      case "profile":
      default:
        return (
          <div className="flex items-center shadow-xl border rounded-full">
            <div className="relative w-8 h-8 rounded-full overflow-hidden cursor-pointer group">
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
        );
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 flex justify-between items-center py-3 px-[3.25%] bg-white shadow-sm backdrop-blur-sm z-50 sm:py-4 sm:px-[7.5%]">
      <div className="flex items-center">
        {onBackClick && <CircleIconButton icon={ChevronLeft} onClick={onBackClick} />}

        <div className="ml-4 flex items-center text-2xl">
          <h1 className="font-medium text-gray-800">{title}</h1>
        </div>
      </div>

      {renderRightElement()}
    </header>
  );
};

export default Header;
