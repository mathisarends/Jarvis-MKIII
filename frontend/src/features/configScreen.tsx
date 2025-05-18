import React from "react";

const ConfigScreen: React.FC = () => {
  return (
    <div className="pt-16 pb-20 px-4">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">Config</h2>
      <div className="bg-white rounded-xl p-4 shadow-md">
        <p className="text-gray-700">Willkommen bei Jarvis, deinem persönlichen Schlaf-Assistenten.</p>

        <div className="mt-4 bg-gray-50 rounded-lg p-3">
          <p className="text-sm text-gray-500 mb-2">Nächster Wecker</p>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-xl text-gray-800 font-bold">07:30</span>
              <span className="text-teal-500 text-xs">Mo, Di, Mi, Do, Fr</span>
            </div>
            <div className="bg-blue-600 text-white text-xs px-2 py-1 rounded">Aktiv</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfigScreen;
