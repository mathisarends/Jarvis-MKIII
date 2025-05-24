import React, { useState, useEffect, useCallback } from "react";
import { Clock, Plus } from "lucide-react";
import SleepScheduleItem from "../components/SleepScheduleItem";
import ActiveAlarmBar from "../components/ActiveAlarmBar";
import { useHeader } from "../contexts/headerContext";
import { useToast } from "../contexts/ToastContext";
import TimePickerModal from "../components/TimePickerModal";
import { alarmApi } from "../api/alarmApi";
import type { AlarmStatus } from "../api/alarmModels";
import Spinner from "../components/Spinner";

const AlarmScreen: React.FC = () => {
  const { updateConfig, resetConfig } = useHeader();
  const { success, error: showError } = useToast();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [alarms, setAlarms] = useState<AlarmStatus[]>([]);
  const [loading, setLoading] = useState(true);

  const [activeAlarm, setActiveAlarm] = useState<{
    isActive: boolean;
    alarmName: string;
    duration: number;
  } | null>(null);

  const loadAlarms = useCallback(async () => {
    try {
      setLoading(true);
      const response = await alarmApi.getAll();
      setAlarms(response.alarms);
    } catch (err) {
      console.error("Failed to load alarms:", err);
      showError("Fehler beim Laden der Alarme");
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    loadAlarms();
  }, [loadAlarms]);

  const handleToggleAlarm = async (alarmId: string, currentActive: boolean) => {
    try {
      setAlarms((prev) =>
        prev.map((alarm) => (alarm.alarm_id === alarmId ? { ...alarm, active: !currentActive } : alarm))
      );

      await alarmApi.toggle(alarmId, !currentActive);

      success(!currentActive ? "Alarm aktiviert" : "Alarm deaktiviert");
      await loadAlarms();
    } catch (err) {
      console.error("Failed to toggle alarm:", err);
      showError("Fehler beim Umschalten des Alarms");

      setAlarms((prev) =>
        prev.map((alarm) => (alarm.alarm_id === alarmId ? { ...alarm, active: currentActive } : alarm))
      );
    }
  };

  const handleDeleteAlarm = async (alarmId: string) => {
    try {
      setAlarms((prev) => prev.filter((alarm) => alarm.alarm_id !== alarmId));

      await alarmApi.delete(alarmId);

      success("Alarm gelöscht");
      await loadAlarms();
    } catch (err) {
      console.error("Failed to delete alarm:", err);
      showError("Fehler beim Löschen des Alarms");
      await loadAlarms();
    }
  };

  const openModal = useCallback(() => {
    setIsModalOpen(true);
  }, []);

  const handleAddAlarm = async (time: string) => {
    try {
      await alarmApi.create({ time });

      success(`Alarm für ${time} erstellt`);
      await loadAlarms();
      setIsModalOpen(false);
    } catch (err: any) {
      console.error("Failed to create alarm:", err);

      if (err.response?.status === 409) {
        showError(`Alarm für ${time} existiert bereits`);
      } else if (err.response?.status === 422) {
        showError("Ungültiges Zeitformat");
      } else {
        showError("Fehler beim Erstellen des Alarms");
      }
    }
  };

  const stopActiveAlarm = () => {
    console.log("🛑 Stopping alarm...");
    setActiveAlarm(null);

    // Hier würdest du das Backend aufrufen:
    // await alarmApi.stopCurrentAlarm();
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

  if (loading) {
    return <Spinner />;
  }

  return (
    <div className="space-y-6">
      {/* Active Alarm Bar - Minimal */}
      {activeAlarm && <ActiveAlarmBar totalDuration={activeAlarm.duration} onStop={stopActiveAlarm} />}

      {/* Empty State */}
      {alarms.length === 0 && (
        <div className="w-full p-6 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-center mb-3">
            <Clock className="h-5 w-5 text-gray-400 mr-3" />
            <h3 className="text-lg font-medium text-gray-800">Noch keine Alarme eingerichtet</h3>
          </div>
          <p className="text-gray-600 text-sm">Erstelle deinen ersten Alarm über das Plus-Symbol oben rechts.</p>
        </div>
      )}

      {/* Grid Layout for Alarms */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-6xl">
        {alarms.map((alarm) => (
          <SleepScheduleItem
            key={alarm.alarm_id}
            time={alarm.time}
            isEnabled={alarm.active}
            onToggle={() => handleToggleAlarm(alarm.alarm_id, alarm.active)}
            onDelete={() => handleDeleteAlarm(alarm.alarm_id)}
            timeUntil={alarm.time_until}
            scheduled={alarm.scheduled}
          />
        ))}
      </div>

      <TimePickerModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSave={handleAddAlarm} />
    </div>
  );
};

export default AlarmScreen;
