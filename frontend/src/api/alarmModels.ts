export interface AlarmStatus {
  alarm_id: string;
  time: string;
  active: boolean;
  scheduled: boolean;
  next_execution: string | null;
  time_until: string | null;
}

export interface AllAlarmsResponse {
  alarms: AlarmStatus[];
  global_settings: {
    wake_up_timer_duration: number;
    use_sunrise: boolean;
    max_brightness: number;
    volume: number;
    wake_up_sound_id: string;
    get_up_sound_id: string;
  };
}

export interface CreateAlarmRequest {
  time: string; // "HH:MM" or "+X"
}

export interface CreateAlarmResponse {
  message: string;
  alarm_id: string;
  time: string;
  active: boolean;
  scheduled: boolean;
  next_execution: string | null;
  settings_used: {
    wake_up_sound: string;
    get_up_sound: string;
    volume: number;
    brightness: number;
    wake_up_duration: string;
    sunrise: string;
  };
}

export interface ToggleAlarmResponse {
  message: string;
  alarm_id: string;
  time: string;
  active: boolean;
  scheduled: boolean;
  next_execution: string | null;
}

export interface DeleteAlarmResponse {
  message: string;
  alarm_id: string;
}
