from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class PredictRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    image_id: str = Field(min_length=1, max_length=128)
    threshold: float = Field(default=0.65, ge=0, le=1)

class Detection(BaseModel):
    id: str
    class_name: str = Field(alias='class')
    confidence: float = Field(ge=0, le=1)
    geometry: dict
    road_segment_ids: list[str] = Field(default_factory=list)
    review_status: Literal['unverified'] = 'unverified'

class ModelProvenance(BaseModel):
    native_tile_size: int | None = None
    model_id: str
    checkpoint_id: str | None = None
    run_id: str | None = None
    task: str
    requires_road_roi: bool
    label_map: dict[str, str] = Field(default_factory=dict)
    identity_status: str

class Prediction(BaseModel):
    image_id: str
    model_version: str
    model_provenance: ModelProvenance | None = None
    inference_mode: Literal['real', 'mock']
    crs: str
    image_width: int
    image_height: int
    source: dict
    detections: list[Detection]
    latency_ms: float
    warnings: list[str] = Field(default_factory=list)
