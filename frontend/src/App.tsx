import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import HomeScreen from "./features/homeScreen";
import AlarmScreen from "./features/alarmScreen";
import NavbarComponent from "./components/Navbar";
import HeaderWrapper from "./components/HeaderWrapper";
import AppLayout from "./layout/app-layout";

function App() {
  return (
    <Router>
      <HeaderWrapper />
      <AppLayout>
        <Routes>
          <Route path="/" element={<HomeScreen />} />
          <Route path="/alarm" element={<AlarmScreen />} />
          {/* ... */}
        </Routes>
      </AppLayout>

      <NavbarComponentWithRouter />
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
