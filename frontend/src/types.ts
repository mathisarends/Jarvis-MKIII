export interface Alarm {
  alarm_id: string;
  time: string;
  wake_up_sound_id: string;
  get_up_sound_id: string;
  volume: number;
  max_brightness: number;
  wake_up_timer_duration: number;
}

export interface SoundOption {
  id: string;
  label: string;
}

export interface AlarmOptions {
  wake_up_sounds: SoundOption[];
  get_up_sounds: SoundOption[];
  volume_range: {
    min: number;
    max: number;
    default: number;
  };
  brightness_range: {
    min: number;
    max: number;
    default: number;
  };
}
