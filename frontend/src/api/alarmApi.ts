// api/client.ts
import axios from "axios";
import type { AxiosInstance } from "axios";
import type { Alarm, AlarmOptions } from "../types";

const API_BASE_URL = "http://192.168.178.64:8000";

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error("[API] Request error:", error);
    return Promise.reject(error);
  }
);

export const alarmApi = {
  getOptions: async (): Promise<AlarmOptions> => {
    const response = await api.get("/alarms/options");
    return response.data;
  },

  getAll: async (): Promise<Alarm[]> => {
    const response = await api.get("/alarms");
    return response.data.alarm_ids.map((id: string) => ({
      alarm_id: id,
      // Add more fields when backend provides them
    }));
  },

  create: async (alarm: Alarm): Promise<Alarm> => {
    const response = await api.post("/alarms", alarm);
    return response.data;
  },

  delete: async (alarmId: string): Promise<void> => {
    await api.delete(`/alarms/${alarmId}`);
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
