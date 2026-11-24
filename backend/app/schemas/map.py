from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MapFeatureWrite(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    description: str
    producer: str | None = None
    ceded_to: str | None = None
    shape: Literal["polygon", "circle"]
    fill_color: str = Field(max_length=20)
    # [[lat, lng], ...] for polygons; [lat, lng] for circles.
    coordinates: list[Any]
    radius_m: int | None = None
    position: int = 0

    @model_validator(mode="after")
    def _validate_shape(self) -> "MapFeatureWrite":
        if self.shape == "circle":
            if self.radius_m is None:
                raise ValueError("circle features require radius_m")
            if len(self.coordinates) != 2 or not all(
                isinstance(c, (int, float)) for c in self.coordinates
            ):
                raise ValueError("circle coordinates must be [lat, lng]")
        else:
            if self.radius_m is not None:
                raise ValueError("polygon features must not set radius_m")
            if len(self.coordinates) < 3 or not all(
                isinstance(p, list) and len(p) == 2 for p in self.coordinates
            ):
                raise ValueError("polygon coordinates must be a list of [lat, lng] pairs")
        return self


class MapFeatureRead(MapFeatureWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int


class MapRegionWrite(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    center_lat: float
    center_lng: float
    zoom: int
    note: str
    position: int = 0
    features: list[MapFeatureWrite] = []


class MapRegionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    center_lat: float
    center_lng: float
    zoom: int
    note: str
    position: int
    features: list[MapFeatureRead]
