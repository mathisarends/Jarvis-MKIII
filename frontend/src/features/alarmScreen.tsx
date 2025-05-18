import React, { useState } from "react";
import SleepScheduleItem from "../components/SleepScheduleItem";

// Hier ein Grid draus machen und das Erstellen von einem neune Alarm erlauben
const AlarmScreen: React.FC = () => {
  const [alarms, setAlarms] = useState([
    { id: 1, time: "23:15", isEnabled: true },
    { id: 2, time: "07:30", isEnabled: false },
  ]);

  const handleToggleAlarm = (id: number) => {
    setAlarms((prevAlarms) =>
      prevAlarms.map((alarm) => (alarm.id === id ? { ...alarm, isEnabled: !alarm.isEnabled } : alarm))
    );
  };

  return (
    <div>
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

      {/* Anzeige, wenn keine Alarme vorhanden sind */}
      {alarms.length === 0 && (
        <div className="text-center py-8 text-gray-500">Keine Alarme eingerichtet. Erstelle deinen ersten Alarm!</div>
      )}
    </div>
  );
};

export default AlarmScreen;
