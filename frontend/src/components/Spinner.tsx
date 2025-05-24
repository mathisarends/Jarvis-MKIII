import React from "react";

const Spinner: React.FC = () => {
  return (
    <div className="fixed inset-0 bg-white bg-opacity-90 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full border-b-2 border-gray-900 h-12 w-12 mx-auto mb-4" />
        <p className="text-gray-600">Lädt...</p>
      </div>
    </div>
  );
};

export default Spinner;
