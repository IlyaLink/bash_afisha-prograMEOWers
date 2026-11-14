"""Справочники городов, категорий и площадок с кешированием (ТЗ 6.3)."""

from typing import List
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.models.reference import Category, City, Venue
from src.schemas.reference import CategoryRead, CityRead, VenueRead

router = APIRouter(tags=["References"])


@router.get(
    "/cities",
    response_model=List[CityRead],
    summary="Справочник городов Башкортостана",
)
async def get_cities(response: Response, db: AsyncSession = Depends(get_db_session)):
    stmt = select(City).where(City.is_active.is_(True)).order_by(City.sort_order.asc(), City.name.asc())
    cities = (await db.execute(stmt)).scalars().all()
    response.headers["Cache-Control"] = "public, max-age=3600"
    return cities


@router.get(
    "/categories",
    response_model=List[CategoryRead],
    summary="Справочник категорий мероприятий",
)
async def get_categories(response: Response, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order.asc())
    categories = (await db.execute(stmt)).scalars().all()
    response.headers["Cache-Control"] = "public, max-age=3600"
    return categories


@router.get(
    "/venues",
    response_model=List[VenueRead],
    summary="Справочник площадок и учреждений культуры",
)
async def get_venues(response: Response, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Venue).order_by(Venue.city_name.asc(), Venue.name.asc())
    venues = (await db.execute(stmt)).scalars().all()
    response.headers["Cache-Control"] = "public, max-age=3600"
    return venues
