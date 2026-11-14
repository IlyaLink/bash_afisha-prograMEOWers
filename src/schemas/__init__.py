"""Экспорт всех Pydantic схем."""

from src.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
    HealthResponse,
)
from src.schemas.reference import CityRead, CategoryRead, VenueRead
from src.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionRead,
    FeedbackCreate,
    FeedbackRead,
)
from src.schemas.event import (
    EventBase,
    EventCreate,
    EventUpdate,
    EventRead,
    EventSourceRead,
    EventListResponse,
)
from src.schemas.import_report import ImportReport, ImportRejectedItem

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "PaginationMeta",
    "HealthResponse",
    "CityRead",
    "CategoryRead",
    "VenueRead",
    "SubscriptionCreate",
    "SubscriptionRead",
    "FeedbackCreate",
    "FeedbackRead",
    "EventBase",
    "EventCreate",
    "EventUpdate",
    "EventRead",
    "EventSourceRead",
    "EventListResponse",
    "ImportReport",
    "ImportRejectedItem",
]
