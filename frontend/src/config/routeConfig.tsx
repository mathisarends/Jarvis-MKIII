import React from "react";
import { Home, AlarmClock, Lightbulb, Volume2 } from "lucide-react";
import AlarmScreen from "../features/alarmScreen";
import LightConfigScreen from "../features/LightConfigScreen";
import SoundConfigScreen from "../features/SoundConfigScreen";

export interface RouteConfig {
  path: string;
  element: React.ReactNode;
  title: string;
  navPath?: string;
  showInNavbar?: boolean;
  icon?: React.ReactNode;
}

export const routes: RouteConfig[] = [
  {
    path: "/",
    element: <AlarmScreen />,
    title: "Wecker",
    showInNavbar: true,
    icon: <AlarmClock size={22} />,
  },
  {
    path: "/sound-config",
    element: <SoundConfigScreen />,
    title: "Sound",
    showInNavbar: true,
    icon: <Volume2 size={22} />,
  },
  {
    path: "/light-config",
    element: <LightConfigScreen />,
    title: "Licht",
    showInNavbar: true,
    icon: <Lightbulb size={22} />,
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
