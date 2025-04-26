from typing import TypedDict, Literal, Optional, Dict, Any

class AudioDeltaResponse(TypedDict):
    type: Literal["response.audio.delta"]
    delta: str

class DoneResponseWithToolCall(TypedDict):
    type: Literal["response.done"]
    response: Dict[str, Any]


class FunctionCallItem(TypedDict):
    type: Literal["function_call"]
    name: Optional[str]
    call_id: str
    arguments: str
    