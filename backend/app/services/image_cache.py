import hashlib
import httpx
from pathlib import Path
from PIL import Image
import io
from typing import Optional
from app.config import BASE_DIR

CACHE_DIR = BASE_DIR / "image_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def cache_path(url: str) -> Path:
    ext = url.split("?")[0].split(".")[-1]
    if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        ext = "bin"
    return CACHE_DIR / f"{_cache_key(url)}.{ext}"


def download_and_cache(url: str, timeout: float = 60.0) -> Optional[bytes]:
    path = cache_path(url)
    if path.exists():
        return path.read_bytes()

    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        if resp.status_code != 200:
            return None
        content_type = resp.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            return None
        path.write_bytes(resp.content)
        return resp.content
    except Exception:
        return None


def load_image(url: str) -> Optional[Image.Image]:
    data = download_and_cache(url)
    if not data:
        return None
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return None


def resolve_image_url(base_url: str, preferred_extension: Optional[str] = None) -> Optional[str]:
    """Find a working image URL by trying common extensions."""
    if "." in base_url.split("?")[0].split("/")[-1]:
        return base_url if _probe_url(base_url) else None

    extensions = [preferred_extension] if preferred_extension else []
    for ext in ["png", "jpg", "jpeg", "webp"]:
        if ext not in extensions:
            extensions.append(ext)

    for ext in extensions:
        if not ext:
            continue
        url = f"{base_url}.{ext}"
        if _probe_url(url):
            return url
    return None


def _probe_url(url: str, timeout: float = 10.0) -> bool:
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        return resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/")
    except Exception:
        return False


def clear_cache():
    for f in CACHE_DIR.glob("*"):
        f.unlink()
