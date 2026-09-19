import io
import re
import threading
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

_reader = None
_reader_lock = threading.Lock()


def _get_engine():
    global _reader
    if _reader is None:
        with _reader_lock:
            if _reader is None:
                from rapidocr_onnxruntime import RapidOCR
                _reader = RapidOCR()
    return _reader


def available() -> bool:
    try:
        return _get_engine() is not None
    except Exception:
        return False


def ocr_text_lines(image: Image.Image) -> List[Tuple[str, float, List[List[int]], str]]:
    """Run RapidOCR on a PIL image.

    Returns list of (text, confidence, bbox, region) where bbox is a quad of
    (x, y) points and region is one of: top, title, middle, bottom.

    On an ONNX inference allocation failure (e.g. 'bad allocation' from the
    ConvTranspose node under CPU memory pressure) it retries once with a smaller
    image, mirroring production behavior where OCR is best-effort.
    """
    engine = _get_engine()
    img = image.convert("RGB")

    attempt_sizes = [1100, 800]
    last_error = None
    for idx, max_side in enumerate(attempt_sizes):
        try:
            if idx > 0:
                # Rebuild the engine: an allocation failure can leave the
                # session in a broken state before the retry.
                _reset_engine()
                engine = _get_engine()
            candidate = img
            if max(img.size) > max_side:
                ratio = max_side / max(img.size)
                candidate = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))))
            arr = np.array(candidate)
            result, _elapse = engine(arr)
            if not result:
                return []
            h, w = arr.shape[:2]
            out = []
            for row in result:
                bbox, text, conf = row[0], row[1], row[2]
                if not text or not bbox:
                    continue
                y_top = min(p[1] for p in bbox)
                y_bot = max(p[1] for p in bbox)
                cy = (y_top + y_bot) / 2.0
                region = "middle"
                if cy < h * 0.24:
                    region = "top"
                elif cy < h * 0.44:
                    region = "title"
                elif cy > h * 0.80:
                    region = "bottom"
                out.append((text, float(conf), bbox, region))
            return out
        except Exception as e:
            last_error = e
            # Retry with the next (smaller) size on inference allocation failures.
    raise last_error if last_error else RuntimeError("OCR failed")


def _reset_engine():
    global _reader
    with _reader_lock:
        _reader = None


def find_collector(line_text: str) -> Optional[str]:
    """Extract a collector number like '4/102' from OCR text (CleanedTypoText)."""
    m = re.search(r"(\d{1,3})\s*/\s*(\d{1,3})", line_text)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}"
    return None


def guess_card_name(lines: List[Tuple[str, float, List[List[int]], str]]) -> Optional[str]:
    """Extract the best card-name token from top/title region OCR text."""
    from app.services.textmatcher import extract_card_name_candidates
    cands = extract_card_name_candidates(lines)
    return cands[0][0] if cands else None