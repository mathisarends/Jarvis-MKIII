// api/client.ts
import axios from "axios";
import type { AxiosInstance } from "axios";
import type { AlarmOptions } from "../types";
import type {
  AllAlarmsResponse,
  CreateAlarmRequest,
  CreateAlarmResponse,
  DeleteAlarmResponse,
  ToggleAlarmResponse,
} from "./alarm_models";

const API_BASE_URL = "http://192.168.178.64:8000";

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

export const alarmApi = {
  getOptions: async (): Promise<AlarmOptions> => {
    const response = await api.get("/alarms/options");
    return response.data;
  },

  getAll: async (): Promise<AllAlarmsResponse> => {
    const response = await api.get("/alarms/");
    return response.data;
  },

  create: async (request: CreateAlarmRequest): Promise<CreateAlarmResponse> => {
    const response = await api.post("/alarms/", request);
    return response.data;
  },

  toggle: async (alarmId: string, active: boolean): Promise<ToggleAlarmResponse> => {
    const response = await api.put(`/alarms/${alarmId}/toggle`, null, {
      params: { active },
    });
    return response.data;
  },

  delete: async (alarmId: string): Promise<DeleteAlarmResponse> => {
    const response = await api.delete(`/alarms/${alarmId}`);
    return response.data;
  },

  createByTime: async (time: string): Promise<CreateAlarmResponse> => {
    return alarmApi.create({ time });
  },

  activate: async (alarmId: string): Promise<ToggleAlarmResponse> => {
    return alarmApi.toggle(alarmId, true);
  },

  deactivate: async (alarmId: string): Promise<ToggleAlarmResponse> => {
    return alarmApi.toggle(alarmId, false);
  },
};

export const soundApi = {
  play: async (soundId: string): Promise<void> => {
    await api.post(`/alarms/play/${encodeURIComponent(soundId)}`);
  },

  stop: async (): Promise<void> => {
    await api.post("/alarms/stop");
  },

  getUrl: (soundId: string): string => {
    return `${API_BASE_URL}/alarms/sounds?sound_id=${encodeURIComponent(soundId)}`;
  },
};

export const settingsApi = {
  getGlobal: async (): Promise<{
    wake_up_timer_duration: number;
    use_sunrise: boolean;
    max_brightness: number;
    volume: number;
    wake_up_sound_id: string;
    get_up_sound_id: string;
  }> => {
    const response = await api.get("/alarms/settings");
    return response.data;
  },

  setBrightness: async (brightness: number): Promise<{ message: string; brightness: number }> => {
    const response = await api.put("/alarms/settings/brightness", {
      brightness: brightness,
    });
    return response.data;
  },

  setVolume: async (volume: number): Promise<{ message: string; volume: number }> => {
    const response = await api.put("/alarms/settings/volume", {
      volume: volume,
    });
    return response.data;
  },

  setWakeUpSound: async (soundId: string): Promise<{ message: string; wake_up_sound_id: string }> => {
    const response = await api.put("/alarms/settings/wake-up-sound", {
      sound_id: soundId,
    });
    return response.data;
  },

  setGetUpSound: async (soundId: string): Promise<{ message: string; get_up_sound_id: string }> => {
    const response = await api.put("/alarms/settings/get-up-sound", {
      sound_id: soundId,
    });
    return response.data;
  },
};
