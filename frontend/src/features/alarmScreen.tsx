import React, { useState, useEffect, useCallback } from "react";
import { Plus } from "lucide-react";
import SleepScheduleItem from "../components/SleepScheduleItem";
import { useHeader } from "../contexts/headerContext";
import TimePickerModal from "../components/TimePickerModal";

const AlarmScreen: React.FC = () => {
  const { updateConfig, resetConfig } = useHeader();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const [alarms, setAlarms] = useState([
    { id: 1, time: "23:15", isEnabled: true },
    { id: 2, time: "07:30", isEnabled: false },
  ]);

  const handleToggleAlarm = (id: number) => {
    setAlarms((prevAlarms) =>
      prevAlarms.map((alarm) => (alarm.id === id ? { ...alarm, isEnabled: !alarm.isEnabled } : alarm))
    );
  };

  const openModal = useCallback(() => {
    setIsModalOpen(true);
  }, []);

  const handleAddAlarm = (time: string) => {
    const newId = Math.max(0, ...alarms.map((alarm) => alarm.id)) + 1;

    const newAlarm = {
      id: newId,
      time: time,
      isEnabled: true,
    };

    setAlarms([...alarms, newAlarm]);
  };

  useEffect(() => {
    updateConfig({
      rightElement: "button",
      buttonIcon: Plus,
      buttonCallback: openModal,
    });

    return () => {
      resetConfig();
    };
  }, [updateConfig, resetConfig, openModal]);

  return (
    <div>
      {/* Grid Layout for Alarms */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-6xl">
        {alarms.map((alarm) => (
          <SleepScheduleItem
            key={alarm.id}
            time={alarm.time}
            isEnabled={alarm.isEnabled}
            onToggle={() => handleToggleAlarm(alarm.id)}
          />
        ))}
      </div>

      {/* Empty state */}
      {alarms.length === 0 && (
        <div className="text-center py-16 px-4">
          <div className="bg-gray-50 rounded-lg p-8 max-w-md mx-auto shadow-sm">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Plus className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-700 mb-2">Keine Alarme eingerichtet</h3>
            <p className="text-gray-500">Erstelle deinen ersten Alarm mit dem Plus-Button!</p>
          </div>
        </div>
      )}

      <TimePickerModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSave={handleAddAlarm} />
    </div>
  );
};

export default AlarmScreen;
