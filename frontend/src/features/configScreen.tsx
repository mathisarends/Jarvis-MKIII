import React, { useState, useEffect } from "react";
import { BrightnessSlider, VolumeSlider } from "../components/Slider";
import { SoundSelector } from "../components/SoundSelector";
import { SoundPlaybackProvider } from "../contexts/soundPlaybackContext";
import type { AlarmOptions } from "../types";
import { alarmApi, settingsApi, audioSystemApi } from "../api/alarmApi";
import type { AudioSystem } from "../api/audioSystemModels";
import { AudioSystemSelector } from "../components/audioSystemSelector";

const ConfigScreen: React.FC = () => {
  const [alarmOptions, setAlarmOptions] = useState<AlarmOptions | null>(null);
  const [audioSystems, setAudioSystems] = useState<AudioSystem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [globalSettings, setGlobalSettings] = useState({
    brightness: 100,
    volume: 0.5,
    wakeUpSound: "",
    getUpSound: "",
  });

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        // ✅ Parallel loading mit allen APIs
        const [options, settings, audioSystemsResponse] = await Promise.all([
          alarmApi.getOptions(),
          settingsApi.getGlobal(),
          audioSystemApi.getSystems(),
        ]);

        setAlarmOptions(options);
        setAudioSystems(audioSystemsResponse.systems);
        setGlobalSettings({
          brightness: settings.max_brightness,
          volume: settings.volume,
          wakeUpSound: settings.wake_up_sound_id,
          getUpSound: settings.get_up_sound_id,
        });
      } catch (err) {
        setError("Fehler beim Laden der Daten");
        console.error("Error loading data:", err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const onBrightnessChangeEnd = async (value: number) => {
    try {
      await settingsApi.setBrightness(value);
      setGlobalSettings((prev) => ({ ...prev, brightness: value }));
    } catch (error) {
      console.error("❌ Failed to save brightness:", error);
    }
  };

  const onVolumeChangeEnd = async (value: number) => {
    try {
      await settingsApi.setVolume(value);
      setGlobalSettings((prev) => ({ ...prev, volume: value }));
    } catch (error) {
      console.error("❌ Failed to save volume:", error);
    }
  };

  const onWakeUpSoundChange = async (soundId: string) => {
    try {
      await settingsApi.setWakeUpSound(soundId);
      setGlobalSettings((prev) => ({ ...prev, wakeUpSound: soundId }));
    } catch (error) {
      console.error("❌ Failed to save wake-up sound:", error);
    }
  };

  const onGetUpSoundChange = async (soundId: string) => {
    try {
      await settingsApi.setGetUpSound(soundId);
      setGlobalSettings((prev) => ({ ...prev, getUpSound: soundId }));
    } catch (error) {
      console.error("❌ Failed to save get-up sound:", error);
    }
  };

  const onAudioSystemChange = async (systemId: string) => {
    try {
      await audioSystemApi.switchSystem(systemId);

      // Update local state
      setAudioSystems((prev) =>
        prev.map((system) => ({
          ...system,
          active: system.id === systemId,
        }))
      );

      // Reload audio systems to get server state
      const response = await audioSystemApi.getSystems();
      setAudioSystems(response.systems);
    } catch (error) {
      console.error("❌ Failed to switch audio system:", error);

      // Reload on error to sync with server
      try {
        const response = await audioSystemApi.getSystems();
        setAudioSystems(response.systems);
      } catch (reloadError) {
        console.error("❌ Failed to reload audio systems:", reloadError);
      }
    }
  };

  // Live updates (für smooth UX)
  const onBrightnessChange = (value: number) => {
    setGlobalSettings((prev) => ({ ...prev, brightness: value }));
  };

  const onVolumeChange = (value: number) => {
    setGlobalSettings((prev) => ({ ...prev, volume: value }));
  };

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
      <div className="flex flex-col gap-5">
        {/* Audio System Selection */}
        <AudioSystemSelector systems={audioSystems} onSystemChange={onAudioSystemChange} />

        <BrightnessSlider
          min={alarmOptions.brightness_range.min}
          max={alarmOptions.brightness_range.max}
          value={globalSettings.brightness}
          onChange={onBrightnessChange}
          onChangeEnd={onBrightnessChangeEnd}
        />
        <VolumeSlider
          min={alarmOptions.volume_range.min}
          max={alarmOptions.volume_range.max}
          value={globalSettings.volume}
          onChange={onVolumeChange}
          onChangeEnd={onVolumeChangeEnd}
        />

        {/* Sound Selectors */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
          <SoundSelector
            title="Wake Up Sounds"
            sounds={alarmOptions.wake_up_sounds}
            selectedSound={globalSettings.wakeUpSound}
            onSoundChange={onWakeUpSoundChange}
          />

          <SoundSelector
            title="Get Up Sounds"
            sounds={alarmOptions.get_up_sounds}
            selectedSound={globalSettings.getUpSound}
            onSoundChange={onGetUpSoundChange}
          />
        </div>
      </div>
    </SoundPlaybackProvider>
  );
};

export default ConfigScreen;
