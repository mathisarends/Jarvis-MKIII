import React, { useState, useEffect } from "react";
import { Volume2, Sun } from "lucide-react";
import Slider from "../components/Slider";
import { SoundSelector } from "../components/SoundSelector";
import { SoundPlaybackProvider } from "../contexts/soundPlaybackContext";
import type { AlarmOptions } from "../types";
import { alarmApi, settingsApi, audioSystemApi } from "../api/alarmApi";
import type { AudioSystem } from "../api/audioSystemModels";
import { AudioSystemSelector } from "../components/audioSystemSelector";
import Spinner from "../components/Spinner";
import { useToast } from "../contexts/ToastContext";
import LightSceneSection from "../components/LightSceneSelection";

const SoundConfigScreen: React.FC = () => {
  const [alarmOptions, setAlarmOptions] = useState<AlarmOptions | null>(null);
  const [audioSystems, setAudioSystems] = useState<AudioSystem[]>([]);
  const [availableScenes, setAvailableScenes] = useState<string[]>([]);
  const [activeScene, setActiveScene] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const { error: showError } = useToast();

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

        const [options, settings, audioSystemsResponse, scenes] = await Promise.all([
          alarmApi.getOptions(),
          settingsApi.getGlobal(),
          audioSystemApi.getSystems(),
          settingsApi.getSceneOptions(),
        ]);

        setAlarmOptions(options);
        setAudioSystems(audioSystemsResponse.systems);
        setAvailableScenes(scenes);
        setGlobalSettings({
          brightness: settings.max_brightness,
          volume: settings.volume, // API gibt 0-1 zurück, das ist korrekt
          wakeUpSound: settings.wake_up_sound_id,
          getUpSound: settings.get_up_sound_id,
        });
      } catch (err) {
        showError("Fehler beim Laden der Daten", "Verbindung fehlgeschlagen");
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

      setAudioSystems((prev) =>
        prev.map((system) => ({
          ...system,
          active: system.id === systemId,
        }))
      );

      const response = await audioSystemApi.getSystems();
      setAudioSystems(response.systems);
    } catch (error) {
      console.error("❌ Failed to switch audio system:", error);

      try {
        const response = await audioSystemApi.getSystems();
        setAudioSystems(response.systems);
      } catch (reloadError) {
        console.error("❌ Failed to reload audio systems:", reloadError);
      }
    }
  };

  const onSceneSelect = async (sceneName: string) => {
    try {
      setActiveScene(sceneName);
      await settingsApi.activateSceneTemporarily(sceneName, 8);
    } catch (error) {
      console.error("❌ Failed to activate scene:", error);
      setActiveScene(null);
    }
  };

  // Live updates (für smooth UX)
  const onBrightnessChange = (value: number) => {
    setGlobalSettings((prev) => ({ ...prev, brightness: value }));
  };

  const onVolumeChange = (value: number) => {
    // Umrechnung: Slider-Wert (0-100) → API-Wert (0-1)
    const apiValue = value / 100;
    setGlobalSettings((prev) => ({ ...prev, volume: apiValue }));
  };

  // Volume für Slider konvertieren (0-1 → 0-100)
  const getVolumeForSlider = () => {
    return Math.round(globalSettings.volume * 100);
  };

  const onVolumeChangeEnd = async (value: number) => {
    try {
      // Umrechnung: Slider-Wert (0-100) → API-Wert (0-1)
      const apiValue = value / 100;
      await settingsApi.setVolume(apiValue);
      setGlobalSettings((prev) => ({ ...prev, volume: apiValue }));
    } catch (error) {
      console.error("❌ Failed to save volume:", error);
    }
  };

  if (loading || !alarmOptions) {
    return <Spinner />;
  }

  return (
    <SoundPlaybackProvider>
      <div className="flex flex-col gap-6">
        <AudioSystemSelector systems={audioSystems} onSystemChange={onAudioSystemChange} />

        <LightSceneSection availableScenes={availableScenes} activeScene={activeScene} onSceneSelect={onSceneSelect} />

        <Slider
          icon={<Sun className="w-4 h-4 text-gray-600" />}
          label="Lamp Brightness"
          min={alarmOptions.brightness_range.min}
          max={alarmOptions.brightness_range.max}
          value={globalSettings.brightness}
          onChange={onBrightnessChange}
          onChangeEnd={onBrightnessChangeEnd}
        />

        <Slider
          icon={<Volume2 className="w-4 h-4 text-gray-600" />}
          label="Alarm Volume"
          min={0}
          max={100}
          value={getVolumeForSlider()}
          onChange={onVolumeChange}
          onChangeEnd={onVolumeChangeEnd}
        />

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

export default SoundConfigScreen;
