import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import HomeScreen from "./features/homeScreen";
import AlarmScreen from "./features/alarmScreen";
import HeaderComponent from "./components/headerComponent";
import NavbarComponent from "./components/navbarComponent";

const HeaderWrapper = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const getTitle = () => {
    switch (location.pathname) {
      case "/":
        return "Home";
      case "/alarm":
        return "Wecker";
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

  return <HeaderComponent title={getTitle()} onBackClick={handleBack} />;
};

function App() {
  return (
    <Router>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <HeaderWrapper />

        <Routes>
          <Route path="/" element={<HomeScreen />} />
          <Route path="/alarm" element={<AlarmScreen />} />
        </Routes>

        <NavbarComponentWithRouter />
      </div>
    </Router>
  );
}

const NavbarComponentWithRouter = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const getActiveRoute = () => {
    const path = location.pathname;
    if (path === "/") {
      return "/home";
    }
    return path;
  };

  const handleNavigation = (route: string) => {
    const targetRoute = route === "/home" ? "/" : route;
    navigate(targetRoute);
  };

  return <NavbarComponent activeRoute={getActiveRoute()} onNavItemClick={handleNavigation} />;
};

export default App;
