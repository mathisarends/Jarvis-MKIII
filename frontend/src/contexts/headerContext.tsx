import React, { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

interface HeaderConfig {
  rightElement: "profile" | "button";
  buttonIcon?: LucideIcon;
  buttonCallback?: () => void;
  buttonLabel?: string;
}

interface HeaderContextType {
  config: HeaderConfig;
  updateConfig: (newConfig: Partial<HeaderConfig>) => void;
  resetConfig: () => void;
}

const defaultConfig: HeaderConfig = {
  rightElement: "profile",
};

const HeaderContext = createContext<HeaderContextType | undefined>(undefined);

export const HeaderProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<HeaderConfig>(defaultConfig);

  const updateConfig = (newConfig: Partial<HeaderConfig>) => {
    setConfig((prevConfig) => ({ ...prevConfig, ...newConfig }));
  };

  const resetConfig = () => {
    setConfig(defaultConfig);
  };

  return <HeaderContext.Provider value={{ config, updateConfig, resetConfig }}>{children}</HeaderContext.Provider>;
};

export const useHeader = () => {
  const context = useContext(HeaderContext);
  if (context === undefined) {
    throw new Error("useHeader must be used within a HeaderProvider");
  }
  return context;
};
