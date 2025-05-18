import React from "react";
import HomeScreen from "../features/homeScreen";
import AlarmScreen from "../features/alarmScreen";
import ConfigScreen from "../features/configScreen";

export interface RouteConfig {
  path: string;
  element: React.ReactNode;
  title: string;
  navPath?: string;
  showInNavbar?: boolean;
  icon?: string;
}

export const routes: RouteConfig[] = [
  {
    path: "/",
    element: <HomeScreen />,
    title: "Home",
    navPath: "/home",
    showInNavbar: true,
    icon: "home-icon",
  },
  {
    path: "/alarm",
    element: <AlarmScreen />,
    title: "Wecker",
    showInNavbar: true,
    icon: "alarm-icon",
  },
  {
    path: "/config",
    element: <ConfigScreen />,
    title: "Konfiguration",
    showInNavbar: true,
    icon: "settings-icon",
  },
];

export const getRouteByPath = (path: string) => {
  return routes.find((route) => route.path === path) || routes.find((route) => route.navPath === path) || routes[0];
};

export const getRouteByNavPath = (navPath: string) => {
  return routes.find((route) => route.navPath === navPath || route.path === navPath) || routes[0];
};

export const getNavbarRoutes = () => {
  return routes.filter((route) => route.showInNavbar);
};
