import React, { useState, useEffect } from "react";
import { BrightnessSlider, VolumeSlider } from "../components/Slider";
import { SoundSelector, SoundPlaybackProvider } from "../components/SoundSelector"; // Provider importieren
import type { AlarmOptions } from "../types";
import { alarmApi } from "../api/alarmApi";

const ConfigScreen: React.FC = () => {
  // State für die geladenen Alarm-Optionen
  const [alarmOptions, setAlarmOptions] = useState<AlarmOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // State für ausgewählte Sounds - verwende IDs statt Dateinamen
  const [selectedWakeUpSound, setSelectedWakeUpSound] = useState<string>("");
  const [selectedGetUpSound, setSelectedGetUpSound] = useState<string>("");

  // Lade Alarm-Optionen beim Component Mount
  useEffect(() => {
    const loadAlarmOptions = async () => {
      try {
        setLoading(true);
        setError(null);
        const options = await alarmApi.getOptions();
        setAlarmOptions(options);

        // Setze Default-Werte, falls verfügbar
        if (options.wake_up_sounds.length > 0) {
          setSelectedWakeUpSound(options.wake_up_sounds[0].id);
        }
        if (options.get_up_sounds.length > 0) {
          setSelectedGetUpSound(options.get_up_sounds[0].id);
        }
      } catch (err) {
        setError("Fehler beim Laden der Alarm-Optionen");
        console.error("Error loading alarm options:", err);
      } finally {
        setLoading(false);
      }
    };

    loadAlarmOptions();
  }, []);

  // Loading State
  if (loading) {
    return (
      <div className="flex flex-col gap-0">
        <div className="flex items-center justify-center p-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
            <p>Lade Alarm-Optionen...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error State
  if (error || !alarmOptions) {
    return (
      <div className="flex flex-col gap-0">
        <div className="flex items-center justify-center p-8">
          <div className="text-center text-red-600">
            <p>{error || "Unbekannter Fehler beim Laden der Daten"}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Erneut versuchen
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <SoundPlaybackProvider>
      {" "}
      {/* 🔥 Provider wrapper für globalen Sound State */}
      <div className="flex flex-col gap-0">
        {/* Sliders */}
        <div className="space-y-3 mb-8">
          <BrightnessSlider
            min={alarmOptions.brightness_range.min}
            max={alarmOptions.brightness_range.max}
            defaultValue={alarmOptions.brightness_range.default}
          />
          <VolumeSlider
            min={alarmOptions.volume_range.min}
            max={alarmOptions.volume_range.max}
            defaultValue={alarmOptions.volume_range.default}
          />
        </div>

        {/* Sound Selectors */}
        <div className="flex flex-col md:flex-row gap-6 w-full">
          <div className="flex-1">
            <SoundSelector
              category="wake-up"
              title="Wake Up Sounds"
              sounds={alarmOptions.wake_up_sounds}
              selectedSound={selectedWakeUpSound}
              onSoundChange={setSelectedWakeUpSound}
            />
          </div>

          <div className="flex-1">
            <SoundSelector
              category="get-up"
              title="Get Up Sounds"
              sounds={alarmOptions.get_up_sounds}
              selectedSound={selectedGetUpSound}
              onSoundChange={setSelectedGetUpSound}
            />
          </div>
        </div>
      </div>
    </SoundPlaybackProvider>
  );
};

export default ConfigScreen;
