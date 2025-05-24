import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import HeaderWrapper from "./components/HeaderWrapper";
import AppLayout from "./layout/app-layout";
import NavbarComponent from "./layout/Navbar";

import { routes } from "./config/routeConfig";
import { HeaderProvider } from "./contexts/headerContext";
import { ToastProvider } from "./contexts/ToastContext";

function App() {
  return (
    <Router>
      <ToastProvider>
        <HeaderProvider>
          <HeaderWrapper />
          <AppLayout>
            <Routes>
              {routes.map((route) => (
                <Route key={route.path} path={route.path} element={route.element} />
              ))}
            </Routes>
          </AppLayout>

          <NavbarComponent />
        </HeaderProvider>
      </ToastProvider>
    </Router>
  );
}

export default App;
