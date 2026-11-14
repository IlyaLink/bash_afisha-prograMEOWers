"""Pydantic схемы справочников."""

import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CityRead(BaseModel):
    id: uuid.UUID
    name: str
    normalized_name: str
    is_active: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class CategoryRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    icon: str
    is_active: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class VenueRead(BaseModel):
    id: uuid.UUID
    name: str
    city_name: str
    address: str
    lat: Optional[float] = None
    lon: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
