from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models import get_db, Card, PricePoint

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/catalog/status")
def catalog_status(db: Session = Depends(get_db)):
    count = db.query(Card).count()
    has_index = False
    try:
        from app.services import index
        index.load_faiss_index()
        has_index = True
    except Exception:
        pass
    return {
        "cards_in_db": count,
        "faiss_index_ready": has_index,
    }


class PricePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price_source: str
    price_type: str
    condition: Optional[str]
    variant: Optional[str]
    currency: str
    price: Optional[float]
    updated_at: Optional[datetime]


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    name: str
    local_id: Optional[str]
    set_code: Optional[str]
    set_name: Optional[str]
    rarity: Optional[str]
    image_url: Optional[str]
    variant: Optional[str]
    prices: List[PricePointOut]


@router.get("/search", response_model=List[CardOut])
def search_cards(
    name: str = Query(...),
    set_code: Optional[str] = Query(None),
    local_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Card).filter(Card.name.ilike(f"%{name}%"))
    if set_code:
        query = query.filter(Card.set_code == set_code)
    if local_id:
        query = query.filter(Card.local_id == local_id)
    return query.all()


@router.get("/{external_id}", response_model=CardOut)
def get_card(external_id: str, db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.external_id == external_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card
