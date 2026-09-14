from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field

# Types de messages Runtime -> HUD
class SetStateMessage(BaseModel):
    type: Literal["set_state"] = "set_state"
    state: Literal["idle", "listening", "thinking", "speaking"]

class VolumeMessage(BaseModel):
    type: Literal["volume"] = "volume"
    value: float = Field(ge=0.0, le=1.0)

class UserSpeechMessage(BaseModel):
    type: Literal["user_speech"] = "user_speech"
    text: str

class SubtitleMessage(BaseModel):
    type: Literal["subtitle"] = "subtitle"
    text: str

class MicStateMessage(BaseModel):
    type: Literal["mic_state"] = "mic_state"
    muted: bool

class ActionMessage(BaseModel):
    type: Literal["action"] = "action"
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None

class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str

class SettingsMessage(BaseModel):
    type: Literal["settings"] = "settings"
    data: Dict[str, Any]

# Types de messages HUD -> Runtime
class UserInputMessage(BaseModel):
    type: Literal["user_input"] = "user_input"
    text: str

class ToggleMicMessage(BaseModel):
    type: Literal["toggle_mic"] = "toggle_mic"
    muted: Optional[bool] = None

class ListMicsMessage(BaseModel):
    type: Literal["list_mics"] = "list_mics"

class SetMicMessage(BaseModel):
    type: Literal["set_mic"] = "set_mic"
    index: Optional[Any] = None

class StopAudioMessage(BaseModel):
    type: Literal["stop_audio"] = "stop_audio"

class GetSettingsMessage(BaseModel):
    type: Literal["get_settings"] = "get_settings"

class UpdateSettingsMessage(BaseModel):
    type: Literal["update_settings"] = "update_settings"
    data: Dict[str, Any]

# Types avec validation activée côté bus (messages HUD -> Runtime typés)
VALIDATORS = {
    "user_input": UserInputMessage,
    "toggle_mic": ToggleMicMessage,
    "list_mics": ListMicsMessage,
    "set_mic": SetMicMessage,
    "update_settings": UpdateSettingsMessage,
}
