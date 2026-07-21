"""OpenRouter client — reuses image_description openrouter_llm + local .env."""

from __future__ import annotations

import base64
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IMG_DESC = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main")

# Prefer gemini flash for schema quality; flash-lite for cheap vision bulk later.
DEFAULT_TEXT_MODEL = "google/gemini-2.5-flash"
DEFAULT_VISION_MODEL = "google/gemini-2.5-flash"
# print_pattern: flash-lite лучше отличает люрекс от меланжа (pilot 100889).
VISION_MODEL_BY_ATTR = {
    "hood": "google/gemini-2.5-flash",
    "length": "google/gemini-2.5-flash",
    # primary pattern model; lurex verify uses flash-lite in extract_vision
    "print_pattern": "google/gemini-2.5-flash",
}
COMPARE_VISION_MODELS = (
    "google/gemini-2.5-flash",
    "google/gemini-2.5-flash-lite",
    "openai/gpt-4o-mini",
)


def vision_model_for_attr(attr_id: str, override: str | None = None) -> str:
    if override:
        return override
    return VISION_MODEL_BY_ATTR.get(attr_id) or DEFAULT_VISION_MODEL


def _ensure_img_desc_path() -> None:
    p = str(IMG_DESC)
    if p not in sys.path:
        sys.path.insert(0, p)


def load_openrouter_key() -> str:
    _ensure_img_desc_path()
    from openrouter_llm import get_openrouter_api_key

    key = get_openrouter_api_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY missing (image_description .env)")
    os.environ.setdefault("OPENROUTER_API_KEY", key)
    return key


def chat_text(
    prompt: str,
    *,
    system: str | None = None,
    model: str = DEFAULT_TEXT_MODEL,
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> str:
    load_openrouter_key()
    _ensure_img_desc_path()
    from openrouter_llm import openrouter_chat

    return openrouter_chat(
        prompt,
        model=model,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
        image_b64=None,
    )


def _image_to_jpeg_b64(path: Path, max_side: int = 768, quality: int = 80) -> str:
    from PIL import Image

    img = Image.open(path).convert("RGB")
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def chat_vision(
    prompt: str,
    *,
    image_path: Path | None = None,
    image_url: str | None = None,
    system: str | None = None,
    model: str = DEFAULT_VISION_MODEL,
    max_tokens: int = 512,
    temperature: float = 0.0,
) -> str:
    """Vision via OpenRouter. Prefer local file → base64; else pass URL through image_description path."""
    load_openrouter_key()
    _ensure_img_desc_path()
    from openrouter_llm import openrouter_chat

    image_b64: str | None = None
    if image_path and Path(image_path).is_file():
        image_b64 = _image_to_jpeg_b64(Path(image_path))
    elif image_url:
        import requests

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://zolla.com/",
        }
        try:
            # Direct to CDN — do not use OpenRouter proxy for product images
            r = requests.get(image_url, timeout=(15, 90), headers=headers)
            r.raise_for_status()
            tmp = Path(ROOT) / "filter_pipeline" / "_tmp_img.jpg"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(r.content)
            image_b64 = _image_to_jpeg_b64(tmp)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        except Exception as e:
            raise RuntimeError(f"failed to download image: {image_url} ({e})") from e

    if not image_b64:
        raise RuntimeError("chat_vision requires image_path or image_url")

    return openrouter_chat(
        prompt,
        image_b64=image_b64,
        model=model,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def parse_json_object(text: str) -> dict[str, Any]:
    if not text:
        return {}
    s = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s)
    if m:
        s = m.group(1).strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {"_list": obj}
    except json.JSONDecodeError:
        pass
    m2 = re.search(r"\{[\s\S]*\}", s)
    if m2:
        try:
            obj = json.loads(m2.group(0))
            return obj if isinstance(obj, dict) else {"_list": obj}
        except json.JSONDecodeError:
            pass
    return {"parse_error": True, "raw_text": text[:3000]}
