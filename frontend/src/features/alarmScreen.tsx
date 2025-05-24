import React, { useState, useEffect, useCallback } from "react";
import { Clock, Plus } from "lucide-react";
import SleepScheduleItem from "../components/SleepScheduleItem";
import { useHeader } from "../contexts/headerContext";
import TimePickerModal from "../components/TimePickerModal";
import { alarmApi } from "../api/alarmApi";
import type { AlarmStatus } from "../api/alarmModels";
import Spinner from "../components/Spinner";

const AlarmScreen: React.FC = () => {
  const { updateConfig, resetConfig } = useHeader();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [alarms, setAlarms] = useState<AlarmStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load alarms from API
  const loadAlarms = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alarmApi.getAll();
      setAlarms(response.alarms);
    } catch (err) {
      console.error("Failed to load alarms:", err);
      setError("Fehler beim Laden der Alarme");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAlarms();
  }, [loadAlarms]);

  const handleToggleAlarm = async (alarmId: string, currentActive: boolean) => {
    try {
      setError(null);
      setAlarms((prev) =>
        prev.map((alarm) => (alarm.alarm_id === alarmId ? { ...alarm, active: !currentActive } : alarm))
      );

      await alarmApi.toggle(alarmId, !currentActive);

      await loadAlarms();
    } catch (err) {
      console.error("Failed to toggle alarm:", err);
      setError("Fehler beim Umschalten des Alarms");

      // Rollback optimistische Änderung
      setAlarms((prev) =>
        prev.map((alarm) => (alarm.alarm_id === alarmId ? { ...alarm, active: currentActive } : alarm))
      );
    }
  };

  const handleDeleteAlarm = async (alarmId: string) => {
    try {
      setError(null);
      setAlarms((prev) => prev.filter((alarm) => alarm.alarm_id !== alarmId));

      await alarmApi.delete(alarmId);

      await loadAlarms();
    } catch (err) {
      console.error("Failed to delete alarm:", err);
      setError("Fehler beim Löschen des Alarms");

      await loadAlarms();
    }
  };

  const openModal = useCallback(() => {
    setIsModalOpen(true);
  }, []);

  const handleAddAlarm = async (time: string) => {
    try {
      setError(null);
      await alarmApi.create({ time });

      await loadAlarms();

      setIsModalOpen(false);
    } catch (err: any) {
      console.error("Failed to create alarm:", err);

      if (err.response?.status === 409) {
        setError(`Alarm für ${time} existiert bereits`);
      } else if (err.response?.status === 422) {
        setError("Ungültiges Zeitformat");
      } else {
        setError("Fehler beim Erstellen des Alarms");
      }
    }
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
    <div>
      {/* Error message */}
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
          <div className="flex justify-between items-center">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
              ×
            </button>
          </div>
        </div>
      )}

      {/* Retry button on error */}
      {error && (
        <div className="mb-4 text-center">
          <button onClick={loadAlarms} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
            Erneut versuchen
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && alarms.length === 0 && (
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

      <TimePickerModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setError(null);
        }}
        onSave={handleAddAlarm}
      />
    </div>
  );
};

export default AlarmScreen;
