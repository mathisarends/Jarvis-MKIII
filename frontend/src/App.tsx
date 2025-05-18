import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import HomeScreen from "./features/homeScreen";
import AlarmScreen from "./features/alarmScreen";
import NavbarComponent from "./components/Navbar";
import HeaderWrapper from "./components/HeaderWrapper";
import Layout from "./layout/layout";

function App() {
  return (
    <Router>
      <div className="max-w-13xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <HeaderWrapper />
        <Routes>
          <Route
            path="/"
            element={
              <Layout>
                <HomeScreen />
              </Layout>
            }
          />
          <Route
            path="/alarm"
            element={
              <Layout>
                <AlarmScreen />
              </Layout>
            }
          />
          {/* ...weitere Screens */}
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
