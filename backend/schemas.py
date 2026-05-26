from typing import Any, Dict, Optional

from pydantic import BaseModel


class ContextIn(BaseModel):
    daw_slot: int = 0
    preset_slot: int = 0
    port_id: int
    channel: int = 0
    bank_msb: int = 0
    bank_lsb: int = 0
    program: int = 0


class SendContextIn(ContextIn):
    # Optional explicit output selection (recommended)
    output_name: Optional[str] = None


class BindingIn(BaseModel):
    id: Optional[int] = None  # If provided, UPDATE by id instead of UPSERT
    context_id: int
    enabled: int = 1
    trig_type: int  # 1 note_on, 2 cc, 3 pitchwheel, 4 program_change
    note: Optional[int] = None
    cc: Optional[int] = None
    value_min: Optional[int] = None
    value_max: Optional[int] = None
    pitch_min: Optional[int] = None
    pitch_max: Optional[int] = None
    command: str
    debounce_ms: int = 200
    require_armed: int = 1
    notes: str = ""
    notify_text: str = ""
    notify_emoji: str = ""


class OutputSelectIn(BaseModel):
    output_name: str


class ActiveContextSetIn(BaseModel):
    context_id: int


class ImportContextIn(BaseModel):
    payload: Dict[str, Any]
    mode: str = "merge"  # "merge" or "replace"


class BindingRunIn(BaseModel):
    binding_id: int
