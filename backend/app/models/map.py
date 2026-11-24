from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, intpk


class MapRegion(Base):
    __tablename__ = "map_regions"

    id: Mapped[intpk]
    lesson_id: Mapped[int] = mapped_column(
        sa.ForeignKey("lessons.id", ondelete="CASCADE")
    )
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True)
    name: Mapped[str] = mapped_column(sa.String(100))
    center_lat: Mapped[float]
    center_lng: Mapped[float]
    zoom: Mapped[int]
    note: Mapped[str] = mapped_column(sa.Text)
    position: Mapped[int] = mapped_column(default=0)

    features: Mapped[list["MapFeature"]] = relationship(
        back_populates="region",
        order_by="MapFeature.position",
        cascade="all, delete-orphan",
    )


class MapFeature(Base):
    __tablename__ = "map_features"

    id: Mapped[intpk]
    region_id: Mapped[int] = mapped_column(
        sa.ForeignKey("map_regions.id", ondelete="CASCADE")
    )
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True)
    name: Mapped[str] = mapped_column(sa.String(150))
    description: Mapped[str] = mapped_column(sa.Text)
    producer: Mapped[str | None] = mapped_column(sa.Text)
    ceded_to: Mapped[str | None] = mapped_column(sa.Text)
    shape: Mapped[str] = mapped_column(sa.String(10))
    fill_color: Mapped[str] = mapped_column(sa.String(20))
    # [[lat, lng], ...] for polygons; [lat, lng] for circles.
    coordinates: Mapped[list[Any]]
    radius_m: Mapped[int | None]
    position: Mapped[int] = mapped_column(default=0)

    region: Mapped[MapRegion] = relationship(back_populates="features")

    __table_args__ = (
        sa.CheckConstraint("shape IN ('polygon', 'circle')", name="shape_valid"),
        sa.CheckConstraint(
            "(shape = 'circle') = (radius_m IS NOT NULL)", name="circle_has_radius"
        ),
    )
