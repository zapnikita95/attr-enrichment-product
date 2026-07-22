#!/usr/bin/env python3
"""Bench vision models for Zolla filters: speed + JSON quality."""
from __future__ import annotations

import base64
import io
import json
import time
import urllib.request
from pathlib import Path

from PIL import Image

OLLAMA = "http://127.0.0.1:11434"
CACHE = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main\projects\Zolla\image_cache")
PROMPT = (
    "Одежда на фото. JSON: {\"attributes\":["
    "{\"attr_id\":\"hood\",\"value\":\"да|нет\"},"
    "{\"attr_id\":\"length\",\"value\":\"mini|midi|maxi|до колена|укороченный\"},"
    "{\"attr_id\":\"print_pattern\",\"value\":\"однотонный|полоска|клетка|горошек|цветочный|геометрия|графика|меланж\"},"
    "{\"attr_id\":\"sleeve_length\",\"value\":\"короткий|длинный|3/4|без рукавов\"},"
    "{\"attr_id\":\"pockets\",\"value\":\"да|нет\"},"
    "{\"attr_id\":\"fastener\",\"value\":\"молния|пуговицы|кнопки|завязки|нет\"},"
    "{\"attr_id\":\"collar\",\"value\":\"круглый|V-образный|стойка|отложной|капюшон|без воротника\"},"
    "{\"attr_id\":\"belt_drawstring\",\"value\":\"да|нет\"},"
    "{\"attr_id\":\"quilted\",\"value\":\"да|нет\"}"
    "]}. value только из списка. Только JSON."
)


def jpeg_b64(path: Path, max_side: int = 512) -> str:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    s = min(1.0, max_side / max(w, h))
    if s < 1:
        im = im.resize((int(w * s), int(h * s)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=72)
    return base64.b64encode(buf.getvalue()).decode()


def show(model: str) -> dict:
    req = urllib.request.Request(
        f"{OLLAMA}/api/show",
        data=json.dumps({"name": model}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def chat(model: str, b64: str, *, think: bool | None = False) -> tuple[float, str, str]:
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 550},
        "messages": [{"role": "user", "content": PROMPT, "images": [b64]}],
    }
    if think is not None:
        payload["think"] = think
    t0 = time.time()
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode())
    msg = d.get("message") or {}
    content = str(msg.get("content") or "")
    thinking = str(msg.get("thinking") or "")
    return round(time.time() - t0, 2), content, thinking


def main() -> None:
    imgs = sorted(CACHE.glob("*.jpg"))[:3]
    if not imgs:
        raise SystemExit("no images")
    models = ["qwen3.5:9b", "qwen3.5:4b", "llava:7b", "gemma4:12b"]
    for m in models:
        try:
            d = show(m)
            det = d.get("details") or {}
            caps = d.get("capabilities") or []
            print(f"SHOW {m} params={det.get('parameter_size')} fam={det.get('families')} caps={caps}")
        except Exception as e:
            print(f"SHOW {m} ERR {e}")

    b64s = [(p, jpeg_b64(p)) for p in imgs]
    for m in models:
        print("=" * 50, m)
        times = []
        for i, (p, b64) in enumerate(b64s):
            try:
                # qwen often needs think=False
                sec, content, thinking = chat(m, b64, think=False)
                times.append(sec)
                preview = (content or thinking)[:220].replace("\n", " ")
                print(f"  [{i}] {sec}s {p.name[:16]}… → {preview!r}")
            except Exception as e:
                print(f"  [{i}] FAIL {e}")
        if times:
            print(f"  avg={sum(times)/len(times):.2f}s")


if __name__ == "__main__":
    main()
