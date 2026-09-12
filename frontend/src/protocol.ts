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

export interface ModelsCatalogMessage {
  type: 'models_catalog';
  options: any[];
  tiers: Record<string, string>;
  choice_mode: string;
}

export interface ProviderModelsMessage {
  type: 'provider_models';
  provider: string;
  ok: boolean;
  models: { id: string; label: string; model: string }[];
  message?: string;
}

export interface AgentThoughtMessage {
  type: 'agent_thought';
  thought: string;
  iteration?: number;
}

export interface AgentPlanMessage {
  type: 'agent_plan';
  status: string;
  query?: string;
  steps?: string[];
}

export interface AgentTokenMessage {
  type: 'agent_token';
  token: string;
  is_final?: boolean;
}

export interface ToolConfirmationRequestMessage {
  type: 'tool_confirmation_request';
  request_id: string;
  tool_name: string;
  description?: string;
  arguments: Record<string, any>;
  danger_level: string;
}

export interface TaskStatusMessage {
  type: 'task_status';
  task_id: string;
  title: string;
  status: string;
  progress: number;
  result?: string;
  error?: string;
}

export interface RoutineTriggeredMessage {
  type: 'routine_triggered';
  id: string;
  name: string;
  time?: string;
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
  | ApiKeyResultMessage
  | ModelsCatalogMessage
  | ProviderModelsMessage
  | AgentThoughtMessage
  | AgentPlanMessage
  | AgentTokenMessage
  | ToolConfirmationRequestMessage
  | TaskStatusMessage
  | RoutineTriggeredMessage;

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

export interface ToolConfirmationResponseMessage {
  type: 'tool_confirmation_response';
  request_id: string;
  confirmed: boolean;
}

