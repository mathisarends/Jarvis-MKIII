export interface AudioSystem {
  id: string;
  name: string;
  description: string;
  active: boolean;
}

export interface AudioSystemsResponse {
  systems: AudioSystem[];
}

export interface SwitchSystemResponse {
  message: string;
  system_id: string;
  system_name: string;
}
