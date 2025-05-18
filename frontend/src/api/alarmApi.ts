import axios from "axios";
import type { Alarm, AlarmOptions } from "../types";

const API_BASE_URL = "http://192.168.178.64:8000";

// Create axios instance with base URL (See how we are gonna do that here.)
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const getAlarmOptions = async (): Promise<AlarmOptions> => {
  const response = await api.get("/alarms/options");
  return response.data;
};

export const getAlarms = async (): Promise<Alarm[]> => {
  const response = await api.get("/alarms");
  return response.data.alarm_ids.map((id: string) => ({
    alarm_id: id,
    // You would typically have another API endpoint to get alarm details
    // This is a placeholder implementation
  }));
};

export const createAlarm = async (alarm: Alarm): Promise<Alarm> => {
  const response = await api.post("/alarms", alarm);
  return response.data;
};

export const deleteAlarm = async (alarmId: string): Promise<void> => {
  await api.delete(`/alarms/${alarmId}`);
};

export const getSoundUrl = (soundId: string): string => {
  return `${API_BASE_URL}/alarms/sounds?sound_id=${encodeURIComponent(soundId)}`;
};
