import io
from pathlib import Path
from typing import List, Optional
import numpy as np
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from app.config import MODEL_NAME

_model: Optional[CLIPModel] = None
_processor: Optional[CLIPProcessor] = None
_embed_lock = None


def get_model():
    global _model, _processor, _embed_lock
    if _model is None or _processor is None:
        _model = CLIPModel.from_pretrained(MODEL_NAME)
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        from threading import Lock
        _embed_lock = Lock()
    return _model, _processor


def _lock():
    global _embed_lock
    if _embed_lock is None:
        get_model()
    return _embed_lock


def embed_image(image_bytes: bytes) -> np.ndarray:
    """Compute a normalized CLIP embedding from raw image bytes."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return embed_image_pil(image)


def embed_image_pil(image: Image.Image) -> np.ndarray:
    model, processor = get_model()
    inputs = processor(images=image, return_tensors="pt")
    pixel_values = inputs["pixel_values"]
    with torch.no_grad():
        vision_outputs = model.vision_model(pixel_values=pixel_values)
        image_features = vision_outputs.pooler_output
        image_features = model.visual_projection(image_features)
    # Normalize for cosine similarity search.
    embedding = image_features / image_features.norm(dim=-1, keepdim=True)
    return embedding.cpu().numpy().astype(np.float32).flatten()


def embed_images_batch(images: List[Image.Image], batch_size: int = 32) -> List[Optional[np.ndarray]]:
    """Embed a list of PIL images in parallel batches (thread-safe, CPU-friendly).

    Returns a list aligned with `images`; any image that fails yields None.
    """
    if not images:
        return []
    model, processor = get_model()
    lock = _lock()
    results: List[Optional[np.ndarray]] = [None] * len(images)
    with lock:
        for start in range(0, len(images), batch_size):
            chunk = images[start:start + batch_size]
            try:
                inputs = processor(images=chunk, return_tensors="pt")
                pixel_values = inputs["pixel_values"]
                with torch.no_grad():
                    feats = model.vision_model(pixel_values=pixel_values).pooler_output
                    feats = model.visual_projection(feats)
                    feats = feats / feats.norm(dim=-1, keepdim=True)
                arrs = feats.cpu().numpy().astype(np.float32)
                for i, arr in enumerate(arrs):
                    results[start + i] = arr.flatten()
            except Exception as e:
                print(f"  batch embed failed at {start}: {e}")
    return results


def embed_text(text: str) -> np.ndarray:
    model, processor = get_model()
    inputs = processor(text=text, return_tensors="pt", padding=True)
    with torch.no_grad():
        text_features = model.get_text_features(**inputs)
    embedding = text_features / text_features.norm(dim=-1, keepdim=True)
    return embedding.cpu().numpy().astype(np.float32).flatten()
