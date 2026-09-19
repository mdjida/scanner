from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base


class Card(Base):
    __tablename__ = "cards"

    id = Column(String, primary_key=True)  # TCGdex card ID
    external_id = Column(String, unique=True, nullable=False, index=True)  # card_id_variant
    name = Column(String, nullable=False, index=True)
    local_id = Column(String, nullable=True)
    set_code = Column(String, nullable=True, index=True)
    set_name = Column(String, nullable=True)
    set_card_count = Column(Integer, nullable=True)
    rarity = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    variant = Column(String, nullable=True)
    language = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    embedding = Column(JSON, nullable=True)

    prices = relationship("PricePoint", back_populates="card", cascade="all, delete-orphan")


class PricePoint(Base):
    __tablename__ = "price_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    card_external_id = Column(String, ForeignKey("cards.external_id"), nullable=False, index=True)
    price_source = Column(String, nullable=False)  # e.g. TCGdex/TCGplayer
    price_type = Column(String, nullable=False)    # e.g. market, low, high
    condition = Column(String, nullable=True)
    variant = Column(String, nullable=True)
    currency = Column(String, nullable=False)
    price = Column(Float, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    card = relationship("Card", back_populates="prices")
