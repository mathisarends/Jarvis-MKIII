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
    <div className="relative">
      {/* Alarm List */}
      <div className="space-y-2">
        {alarms.map((alarm) => (
          <SleepScheduleItem
            key={alarm.id}
            time={alarm.time}
            timeFromNow={`${alarm.id === 1 ? "4h 25m" : "8h 40m"} from now`}
            isEnabled={alarm.isEnabled}
            onToggle={() => handleToggleAlarm(alarm.id)}
          />
        ))}
      </div>

      <TimePickerModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSave={handleAddAlarm} />
    </div>
  );
};

export default AlarmScreen;
