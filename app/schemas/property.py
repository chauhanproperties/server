from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

class BuildingInput(BaseModel):
    bedrooms: int = Field(ge=0)
    kitchens: int = Field(ge=0)
    bathrooms: int = Field(ge=0)
    building_area: float = Field(ge=0)
    garden_area: float = Field(default=0, ge=0)
    parking_area: float = Field(default=0, ge=0)

class PropertyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=240)
    property_type: Literal["plot", "house", "flat"]
    address: str = Field(min_length=1, max_length=1000)
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    description: str | None = Field(default=None, max_length=10000)
    price: float = Field(ge=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    maps_url: str | None = Field(default=None, max_length=2000)
    building_details: BuildingInput | None = None

    @field_validator("maps_url", mode="before")
    @classmethod
    def validate_maps_url(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Maps URL must be a web address")
        value = value.strip()
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Maps URL must start with http:// or https://")
        if len(value) > 2000:
            raise ValueError("Maps URL must be at most 2000 characters")
        return value

    @model_validator(mode="after")
    def building_matches_type(self):
        if self.property_type == "plot" and self.building_details is not None:
            raise ValueError("Plots cannot have building details")
        if self.property_type in {"house", "flat"} and self.building_details is None:
            raise ValueError("House and flat properties require building details")
        return self

class SoldInput(BaseModel):
    buyer_name: str = Field(min_length=1, max_length=200)
    buyer_phone: str = Field(min_length=7, max_length=24)
    buyer_whatsapp_number: str = Field(min_length=7, max_length=24)
    buyer_email: EmailStr | None = None
    sold_at: datetime | None = None
    sale_price: float | None = Field(default=None, ge=0)

class ImageOrderInput(BaseModel):
    image_ids: list[int]
