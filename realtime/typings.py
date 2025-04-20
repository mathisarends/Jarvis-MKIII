from typing import TypedDict, Union, Literal, List, Optional, Dict, Any


class AudioDeltaResponse(TypedDict):
    type: Literal["response.audio.delta"]
    delta: str


class TextDelta(TypedDict, total=False):
    text: str
    annotations: List[Any]
    start: int
    end: int


class TextDeltaResponse(TypedDict):
    type: Literal["response.text.delta"]
    delta: TextDelta


class TranscriptDelta(TypedDict):
    type: Literal["response.audio_transcript.delta"]
    delta: Dict[str, Union[str, int]]


class DoneResponse(TypedDict):
    type: Literal["response.done"]


class ErrorResponse(TypedDict, total=False):
    type: Literal["error"]
    message: Optional[str]
    code: Optional[str]
    data: Optional[Dict[str, Any]]


class DoneResponseWithToolCall(TypedDict):
    type: Literal["response.done"]
    response: Dict[str, Any]


class FunctionCallItem(TypedDict):
    type: Literal["function_call"]
    name: Optional[str]
    call_id: str
    arguments: str


OpenAIRealtimeResponse = Union[
    AudioDeltaResponse,
    TextDeltaResponse,
    TranscriptDelta,
    DoneResponse,
    ErrorResponse,
    Dict[str, Any],  # fallback for untyped cases like session.updated
]
