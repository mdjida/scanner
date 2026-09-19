from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app.models import get_db, Card, PricePoint
from app.services import embeddings, index, identify_service, ocr
from app.routers.cards import CardOut, PricePointOut
from app.services.pricing import build_prices_by_condition

router = APIRouter(prefix="/identify", tags=["identify"])


class CandidateOut(BaseModel):
    score: float
    card: CardOut


class IdentifyResponse(BaseModel):
    best_match: CandidateOut
    candidates: List[CandidateOut]
    confidence: str = "medium"
    verified_by: List[str] = []
    collector: Optional[str] = None
    ocr_name: Optional[str] = None
    prices_by_condition: Optional[dict] = None


@router.post("", response_model=IdentifyResponse)
async def identify_card(
    file: UploadFile = File(...),
    k: int = Query(8, ge=2, le=20),
    use_ocr: int = Query(1, ge=0, le=1),
    prefer_visual: int = Query(0, ge=0, le=1),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image")

    try:
        result = identify_service.identify_image(
            image_bytes,
            db=db,
            k=k,
            use_ocr=bool(use_ocr),
            prefer_visual=bool(prefer_visual),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="FAISS index not built. Run ingestion first.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Identification failed: {e}")

    best = result.get("best_match")
    if not best:
        raise HTTPException(status_code=404, detail="No matching cards found")

    best_card: Card = best["card"]
    best_out = CandidateOut(score=best["score"], card=CardOut.model_validate(best_card))

    candidates_out = []
    for c in result.get("candidates", []):
        try:
            candidates_out.append(CandidateOut(score=c["score"], card=CardOut.model_validate(c["card"])))
        except Exception:
            continue

    prices_by_condition = build_prices_by_condition(best_card)

    return IdentifyResponse(
        best_match=best_out,
        candidates=candidates_out,
        confidence=result.get("confidence", "medium"),
        verified_by=result.get("verified_by", []),
        collector=result.get("collector"),
        ocr_name=result.get("ocr_name"),
        prices_by_condition=prices_by_condition,
    )