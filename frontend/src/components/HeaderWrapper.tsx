// src/components/HeaderWrapper.tsx
import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { getRouteByPath } from "../config/routeConfig";
import Header from "../layout/Header";

const HeaderWrapper: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const currentRoute = getRouteByPath(location.pathname);

  const handleBack = () => {
    navigate(-1);
  };

  const profilePicture = "https://i.pravatar.cc/150?img=3";

  return <Header title={currentRoute.title} onBackClick={handleBack} profilePicture={profilePicture} />;
};

export default HeaderWrapper;
