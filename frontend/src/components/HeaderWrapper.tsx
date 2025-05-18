import { useNavigate, useLocation } from "react-router-dom";
import Header from "./Header";

export const useHeaderService = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Titel basierend auf Route
  const getTitle = () => {
    switch (location.pathname) {
      case "/":
        return "Home";
      case "/alarm":
        return "Alarm Clock";
      case "/stats":
        return "Statistik";
      case "/profile":
        return "Profil";
      default:
        return "Jarvis";
    }
  };

  const handleBack = () => {
    navigate(-1);
  };

  return {
    title: getTitle(),
    onBackClick: handleBack,
  };
};

const HeaderWrapper = () => {
  const headerService = useHeaderService();

  const profilePicture = "https://i.pravatar.cc/150?img=3";

  return <Header title={headerService.title} onBackClick={headerService.onBackClick} profilePicture={profilePicture} />;
};

export default HeaderWrapper;
