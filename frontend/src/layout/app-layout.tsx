import React from "react";

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <main
    className="
      w-full 
      px-[3.25%] 
      py-20
      pb-16 
      min-h-[calc(100vh-4rem)] 
      sm:px-[7.5%] 
      sm:py-24
      "
  >
    {children}
  </main>
);

export default AppLayout;
