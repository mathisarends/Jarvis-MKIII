import React, { useState, useEffect } from "react";
import { Plus } from "lucide-react";
import SleepScheduleItem from "../components/SleepScheduleItem";
import { useHeader } from "../contexts/headerContext"; // Import the header context hook

const AlarmScreen: React.FC = () => {
  // Get header context functions
  const { updateConfig, resetConfig } = useHeader();

  const [alarms, setAlarms] = useState([
    { id: 1, time: "23:15", isEnabled: true },
    { id: 2, time: "07:30", isEnabled: false },
  ]);

  useEffect(() => {
    updateConfig({
      rightElement: "button",
      buttonIcon: Plus,
      buttonCallback: handleAddAlarm,
    });

    return () => {
      resetConfig();
    };
  }, [updateConfig, resetConfig]);

  const handleToggleAlarm = (id: number) => {
    setAlarms((prevAlarms) =>
      prevAlarms.map((alarm) => (alarm.id === id ? { ...alarm, isEnabled: !alarm.isEnabled } : alarm))
    );
  };

  const handleAddAlarm = () => {
    const newId = Math.max(0, ...alarms.map((alarm) => alarm.id)) + 1;

    const newAlarm = {
      id: newId,
      time: "08:00",
      isEnabled: true,
    };

    setAlarms([...alarms, newAlarm]);
  };

  return (
    <div className="relative">
      {/* Bestehende Alarme */}
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
    </div>
  );
};

export default AlarmScreen;
