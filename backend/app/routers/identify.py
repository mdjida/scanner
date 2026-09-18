from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app.models import get_db, Card
from app.services import embeddings, index, identify_service
from app.routers.cards import CardOut

router = APIRouter(prefix="/identify", tags=["identify"])


class CandidateOut(BaseModel):
    score: float
    card: CardOut


class IdentifyResponse(BaseModel):
    best_match: CandidateOut
    candidates: List[CandidateOut]


@router.post("", response_model=IdentifyResponse)
async def identify_card(
    file: UploadFile = File(...),
    k: int = 5,
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image")

    try:
        results = identify_service.identify_image(image_bytes, db=db, k=k)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="FAISS index not built. Run ingestion first.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Identification failed: {e}")

    candidates = []
    for card, score in results:
        candidates.append(CandidateOut(score=score, card=CardOut.model_validate(card)))

    if not candidates:
        raise HTTPException(status_code=404, detail="No matching cards found")

    return IdentifyResponse(best_match=candidates[0], candidates=candidates)
