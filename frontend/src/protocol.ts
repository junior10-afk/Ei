export type AssistantStateType = 'idle' | 'listening' | 'thinking' | 'speaking';

export interface SetStateMessage {
  type: 'set_state';
  state: AssistantStateType;
}

export interface VolumeMessage {
  type: 'volume';
  value: number;
}

export interface UserSpeechMessage {
  type: 'user_speech';
  text: string;
}

export interface SubtitleMessage {
  type: 'subtitle';
  text: string;
}

export interface MicStateMessage {
  type: 'mic_state';
  muted: boolean;
}

export interface ActionMessage {
  type: 'action';
  action: string;
  params: Record<string, any>;
  result?: any;
}

export interface SettingsMessage {
  type: 'settings';
  data: Record<string, any>;
}

export type IncomingMessage =
  | SetStateMessage
  | VolumeMessage
  | UserSpeechMessage
  | SubtitleMessage
  | MicStateMessage
  | ActionMessage
  | SettingsMessage;

export interface UserInputMessage {
  type: 'user_input';
  text: string;
}

export interface ToggleMicMessage {
  type: 'toggle_mic';
  muted?: boolean;
}

export interface StopAudioMessage {
  type: 'stop_audio';
}

export interface UpdateSettingsMessage {
  type: 'update_settings';
  data: Record<string, any>;
}
