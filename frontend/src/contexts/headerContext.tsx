import React, { createContext, useContext, useState, useCallback } from "react";

interface HeaderConfig {
  rightElement: "profile" | "button";
  buttonIcon?: React.ElementType;
  buttonCallback?: () => void;
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

export const HeaderProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<HeaderConfig>(defaultConfig);

  const updateConfig = useCallback((newConfig: Partial<HeaderConfig>) => {
    setConfig((prevConfig) => ({ ...prevConfig, ...newConfig }));
  }, []);

  const resetConfig = useCallback(() => {
    setConfig(defaultConfig);
  }, []);

  const value = React.useMemo(
    () => ({
      config,
      updateConfig,
      resetConfig,
    }),
    [config, updateConfig, resetConfig]
  );

  return <HeaderContext.Provider value={value}>{children}</HeaderContext.Provider>;
};

export const useHeader = () => {
  const context = useContext(HeaderContext);
  if (context === undefined) {
    throw new Error("useHeader must be used within a HeaderProvider");
  }
  return context;
};
