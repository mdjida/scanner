import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.models import engine, SessionLocal, Base
from app.services import ingest


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if "--smoke-test" in sys.argv:
            ingest.ingest_all(db, smoke_test=True)
        else:
            limit = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
            limit_cards = None
            ingest.ingest_all(db, limit_sets=limit, limit_cards_per_set=limit_cards)
    finally:
        db.close()


if __name__ == "__main__":
    main()
