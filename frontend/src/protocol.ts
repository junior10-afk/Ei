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

export interface SystemStatsMessage {
  type: 'system_stats';
  cpu: number;
  ram: number;
}

export interface ModelSelectMessage {
  type: 'model_select';
  task: string;
  tier: string;
  tier_label?: string;
  suggested?: string | null;
  options: any[];
}

export interface ModelUsedMessage {
  type: 'model_used';
  model_id: string;
  label: string;
  tier: string;
}

export interface ModelSelectClosedMessage {
  type: 'model_select_closed';
  model_id: string | null;
}

export interface LongResponseMessage {
  type: 'long_response';
  text: string;
  model?: string;
}

export interface ApiKeyResultMessage {
  type: 'api_key_result';
  provider?: string;
  var?: string;
  ok: boolean;
  message?: string;
}

export type IncomingMessage =
  | SetStateMessage
  | VolumeMessage
  | UserSpeechMessage
  | SubtitleMessage
  | MicStateMessage
  | ActionMessage
  | SettingsMessage
  | SystemStatsMessage
  | ModelSelectMessage
  | ModelUsedMessage
  | ModelSelectClosedMessage
  | LongResponseMessage
  | ApiKeyResultMessage;

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
