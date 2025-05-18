import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import HeaderWrapper from "./components/HeaderWrapper";
import AppLayout from "./layout/app-layout";
import NavbarComponent from "./layout/Navbar";

import { routes } from "./config/routeConfig";

function App() {
  return (
    <Router>
      <HeaderWrapper />
      <AppLayout>
        <Routes>
          {routes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element} />
          ))}
        </Routes>
      </AppLayout>

      <NavbarComponent />
    </Router>
  );
}

export default App;
