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
                try:
                    if len(row) < 3:
                        continue
                    bbox, text, conf = row[0], row[1], row[2]
                    if not text or bbox is None:
                        continue
                    text = str(text)
                    conf = float(conf)
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
                    out.append((text, conf, bbox, region))
                except Exception:
                    # A malformed OCR row should never break a scan.
                    continue
            return out
        except Exception as e:
            last_error = e
            # Retry with the next (smaller) size on inference allocation failures.
    raise last_error if last_error else RuntimeError("OCR failed")


def _reset_engine():
    global _reader
    with _reader_lock:
        _reader = None


def _ocr_typo_fix(text: str) -> str:
    """Fix common OCR confusions that affect collector numbers."""
    # Map letters that look like digits back to digits.
    table = str.maketrans({
        'O': '0', 'o': '0',
        'S': '5', 's': '5',
        'B': '8', 'g': '9',
        'I': '1', 'l': '1',
        'Z': '2', 'z': '2',
    })
    return text.translate(table)


def _is_collector_like(line_text: str) -> bool:
    """True when a line plausibly contains a collector number (digits + a
    separator, or at least 4 digits), so typo-fixing won't corrupt name text."""
    collapsed = re.sub(r'\s+', '', line_text)
    m = re.search(r"(\d{1,3})[/.:-](\d{1,3})", collapsed)
    if m:
        return True
    return len(re.findall(r'\d', collapsed)) >= 4


def find_collector(line_text: str) -> Optional[str]:
    """Extract a collector number like '4/102' from OCR text.

    Also tolerates common separator typos (. - space), inter-digit spaces
    (e.g. '3 8 / 9 5' -> '38/95') and OCR character swaps.
    """
    if not line_text:
        return None
    # Direct match (fast path): 4/102, 4 / 102, 4.102, 4-102
    normalized = line_text.replace('.', '/').replace('-', '/')
    normalized = re.sub(r'\s*/\s*', '/', normalized)
    normalized = re.sub(r'(?i)(?:no\.?|#)\s*', '', normalized)
    m = re.search(r"(\d{1,3})/(\d{1,3})", normalized)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}"

    # Lenient path: collapse all whitespace, fix digit/letter swaps, strip 'no'/'#'.
    if not _is_collector_like(line_text):
        return None
    fixed = _ocr_typo_fix(line_text)
    fixed = re.sub(r'\s+', '', fixed)
    fixed = fixed.replace('.', '/').replace('-', '/')
    fixed = re.sub(r'(?i)^(no\.?|#)', '', fixed)
    m = re.search(r"(\d{1,3})/(\d{1,3})", fixed)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}"
    return None


def _digit_split_candidates(collapsed_digits: str) -> List[str]:
    """Given a digit-only run (maybe with a misread slash or merged digits),
    yield plausible 'NN/DD' collector splits for the set-size matcher to align."""
    out: List[str] = []
    L = len(collapsed_digits)
    if L < 4 or L > 6:
        return out

    def ok(side: str) -> bool:
        return 1 <= len(side) <= 3

    # (a) Adjacent concatenation: num = prefix, den = suffix.
    for j in range(1, L):
        left, right = collapsed_digits[:j], collapsed_digits[j:]
        if ok(left) and ok(right):
            out.append(f"{int(left)}/{int(right)}")
    # (b) One digit position is a misread slash (e.g. '38/95' read as '38795').
    for j in range(1, L - 1):
        left, right = collapsed_digits[:j], collapsed_digits[j + 1:]
        if ok(left) and ok(right):
            out.append(f"{int(left)}/{int(right)}")
    seen: set = set()
    clean = []
    for c in out:
        if c not in seen:
            seen.add(c)
            clean.append(c)
    return clean


def find_collector_candidates(line_text: str) -> List[str]:
    """Return plausible collector strings for one OCR line (best first), using
    the lenient find_collector plus merged/misread digit-run splits."""
    if not line_text:
        return []
    out: List[str] = []
    exact = find_collector(line_text)
    if exact:
        out.append(exact)
    if _is_collector_like(line_text):
        fixed = _ocr_typo_fix(line_text)
        collapsed = re.sub(r"\s+", "", fixed)
        collapsed = collapsed.replace(".", "/").replace("-", "/")
        for run in re.findall(r"\d{4,6}", collapsed):
            for cand in _digit_split_candidates(run):
                if cand not in out:
                    out.append(cand)
    return out


def find_collector_in_lines(lines: List[Tuple[str, float, List[List[int]], str]]) -> List[str]:
    """Search all OCR lines for collector numbers, preferring the bottom region.

    Returns a list of candidate collector strings (deduped, best first). The
    exact set-size alignment happens downstream, which is what tolerates a
    mangled slash ('38795' -> '38/95').
    """
    if not lines:
        return []
    clean: List[Tuple[str, float, str]] = []
    for item in lines:
        if not isinstance(item, (tuple, list)) or len(item) < 4:
            continue
        try:
            text, conf, _bbox, region = item[:4]
            clean.append((str(text), float(conf), region))
        except Exception:
            continue

    # Bottom lines are most likely to contain the collector number.
    bottom_lines = [x for x in clean if x[2] == 'bottom' and x[1] >= 0.5]
    all_lines = sorted(clean, key=lambda x: -x[1])  # highest confidence first

    scored: List[Tuple[str, float]] = []
    for source in (bottom_lines, all_lines):
        for text, conf, _region in source:
            for cand in find_collector_candidates(text):
                scored.append((cand, conf))
        if scored:
            break

    # Best-first: highest-confidence line first.
    scored.sort(key=lambda kv: -kv[1])
    seen: set = set()
    out: List[str] = []
    for cand, _conf in scored:
        if cand not in seen:
            seen.add(cand)
            out.append(cand)
    return out


def ocr_crop_pass(image: Image.Image, region: str = "top") -> List[Tuple[str, float, List[List[int]], str]]:
    """Enlarge a horizontal band (title or collector region) and OCR it again.

    Used when the primary pass came back nearly empty (slim/simple cards like
    Basic Energy), where small text is easily missed. Bboxes are scaled back to
    full-image coordinates.
    """
    try:
        w, h = image.size
        if region == "bottom":
            box = (0, int(h * 0.76), w, h)
        else:
            box = (0, 0, w, int(h * 0.24))
        crop = image.convert("RGB").crop(box)
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
        arr = np.array(crop)
        engine = _get_engine()
        result, _elapse = engine(arr)
        out: List[Tuple[str, float, List[List[int]], str]] = []
        for row in result or []:
            try:
                if len(row) < 3:
                    continue
                bbox, text, conf = row[0], row[1], row[2]
                if not text or bbox is None:
                    continue
                nb = [[float(x) / 3.0, float(y) / 3.0] for x, y in bbox]
                out.append((str(text), float(conf), nb, region))
            except Exception:
                continue
        return out
    except Exception as e:
        print(f"  crop OCR failed: {e}")
        return []


def guess_card_name(lines: List[Tuple[str, float, List[List[int]], str]]) -> Optional[str]:
    """Extract the best card-name token from top/title region OCR text."""
    from app.services.textmatcher import extract_card_name_candidates
    cands = extract_card_name_candidates(lines)
    return cands[0][0] if cands else None