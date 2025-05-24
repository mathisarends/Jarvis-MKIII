import React, { useState, useEffect } from "react";
import { Sun } from "lucide-react";
import Slider from "../components/Slider";
import type { AlarmOptions } from "../types";
import { alarmApi, settingsApi } from "../api/alarmApi";
import Spinner from "../components/Spinner";
import { useToast } from "../contexts/ToastContext";
import LightSceneSection from "../components/LightSceneSelection";

const SoundConfigScreen: React.FC = () => {
  const [alarmOptions, setAlarmOptions] = useState<AlarmOptions | null>(null);
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

        const [options, settings, scenes] = await Promise.all([
          alarmApi.getOptions(),
          settingsApi.getGlobal(),
          settingsApi.getSceneOptions(),
        ]);

        setAlarmOptions(options);
        setAvailableScenes(scenes);
        setGlobalSettings({
          brightness: settings.max_brightness,
          volume: settings.volume,
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

  const onSceneSelect = async (sceneName: string) => {
    try {
      setActiveScene(sceneName);
      await settingsApi.activateSceneTemporarily(sceneName, 8);
    } catch (error) {
      console.error("❌ Failed to activate scene:", error);
      setActiveScene(null);
    }
  };

  const onBrightnessChange = (value: number) => {
    setGlobalSettings((prev) => ({ ...prev, brightness: value }));
  };

  if (loading || !alarmOptions) {
    return <Spinner />;
  }

  return (
    <div className="flex flex-col gap-6">
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
    </div>
  );
};

export default SoundConfigScreen;
