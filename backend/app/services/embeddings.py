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


def get_model():
    global _model, _processor
    if _model is None or _processor is None:
        _model = CLIPModel.from_pretrained(MODEL_NAME)
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    return _model, _processor


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


def embed_text(text: str) -> np.ndarray:
    model, processor = get_model()
    inputs = processor(text=text, return_tensors="pt", padding=True)
    with torch.no_grad():
        text_features = model.get_text_features(**inputs)
    embedding = text_features / text_features.norm(dim=-1, keepdim=True)
    return embedding.cpu().numpy().astype(np.float32).flatten()
