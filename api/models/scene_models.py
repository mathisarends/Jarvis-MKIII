from pydantic import BaseModel


class SceneActivationRequest(BaseModel):
    scene_name: str
    duration: int = 8

class SceneActivationResponse(BaseModel):
    message: str
    scene_name: str
    duration: int