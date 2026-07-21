# -*- coding: utf-8 -*-
"""OpenRouter vision probe for TSUM: what NEW searchable attrs are on photos."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "portfolio" / "tsum"
CAND = OUT / "vision_candidates.json"
ENV_CANDIDATES = [
    Path(r"C:\Users\1\OneDrive\Desktop\image_description-main\.env"),
    Path(r"C:\Users\1\OneDrive\Desktop\attributes_extraction-main\.env"),
]

MODEL = os.environ.get("OR_VISION_MODEL", "google/gemini-2.5-flash")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Prioritize high-search categories; diversify
FOCUS_BUCKETS = [
    "odezhda",
    "platya",
    "obuv",
    "tufli",
    "sumki",
    "parfyumeriya",
    "kosmetika",
    "aksessuary",
    "chasy",
    "ukrasheniya",
    "yuvelirnye",
    "kurtki",
    "palto",
    "dzhinsy",
    "rubashki",
    "bryuki",
    "bizhuteriya",
]

PER_BUCKET = int(os.environ.get("OR_VISION_PER_BUCKET", "2"))
MAX_PRODUCTS = int(os.environ.get("OR_VISION_N", "28"))

# Already in feed at high fill — do NOT extract as new
FEED_ALREADY = [
    "Пол",
    "Цвет / Оттенок (базовый цвет)",
    "Артикул / id-поля",
    "Материал (состав %)",
    "Размер",
    "Страна дизайна",
    "Сезон коллекции (SS/FW)",
    "attribute_length (мини/миди/макси) — где заполнен",
    "attribute_sleeve — где заполнен",
    "attribute_type",
    "attribute_base (подошва обуви) — где заполнен",
    "attribute_clasp — редко",
    "attribute_details — редко (~8%)",
    "custom categories",
    "Бренд (обычно в name/vendor)",
]


def load_api_key() -> str:
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if key:
        return key
    for env in ENV_CANDIDATES:
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("OPENROUTER_API_KEY="):
                return s.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("OPENROUTER_API_KEY not found")


def pick_samples(by_bucket: dict, n: int) -> list[dict]:
    picked: list[dict] = []
    for b in FOCUS_BUCKETS:
        lst = list(by_bucket.get(b) or [])
        for item in lst[:PER_BUCKET]:
            picked.append(item)
            if len(picked) >= n:
                return picked
    # fill from other
    for b, lst in by_bucket.items():
        if b in FOCUS_BUCKETS:
            continue
        for item in lst[:1]:
            picked.append(item)
            if len(picked) >= n:
                return picked
    return picked


def build_prompt(p: dict) -> str:
    params = p.get("params") or {}
    # Drop technical ids from "already have"
    skip = {
        "brand_id",
        "model_id",
        "product_id",
        "color_concrete_id",
        "color_base_id",
        "size_id",
        "date_create",
        "Лого",
        "Штрихкод",
        "Артикул",
    }
    param_lines = [f"- {k}: {v}" for k, v in params.items() if k not in skip][:30]
    already = "\n".join(f"- {x}" for x in FEED_ALREADY)

    return f"""Ты анализируешь фото товара luxury fashion / beauty ритейлера ЦУМ (TSUM).

ЗАДАЧА: найти атрибуты, которые РЕАЛЬНО видны на фото (визуал или OCR этикетки/флакона),
и которых НЕТ в названии и параметрах фида ниже.

НЕ ИЗВЛЕКАЙ (уже в фиде или бесполезно):
{already}
- цену, штрихкод, артикул, id
- бренд если уже в названии
- базовый цвет если уже в params Цвет/Оттенок
- состав % если уже в Материал
- маркетинговые «эмоции», «статус», «роскошь»

НЕ ВКЛЮЧАЙ негации («без X», «не содержит») — ломают поиск.

ИЩИ В ПРИОРИТЕТЕ (только если явно на фото и НЕТ в params/названии):
ОДЕЖДА: принт/узор (клетка, полоска, цветочный, леопард, логомания), силуэт/посадка (оверсайз, slim, А-силуэт),
капюшон, тип воротника/выреза, детали (карманы, пояс, разрезы, пуговицы vs молния если нет clasp),
фактура (стёжка, вязка, плиссе, кружево) если не в материале.
ОБУВЬ: форма носка, высота каблука (визуально), тип застёжки, открытость.
СУМКИ: силуэт (тоут/кроссбоди/багет), фурнитура, количество ручек, наличие ремня.
ПАРФЮМ: концентрация (EDP/EDT) с флакона, ключевые ноты с этикетки, объём если нет в названии.
УКРАШЕНИЯ/ЧАСЫ: тип камня/металла если нет в params, форма корпуса, тип браслета.

НАЗВАНИЕ: {p.get('name')}
КАТЕГОРИЯ: {p.get('category_name')} | bucket={p.get('bucket')} | vendor={p.get('vendor')}

УЖЕ В ФИДЕ (НЕ повторяй):
{chr(10).join(param_lines) if param_lines else '(пусто)'}

Верни ТОЛЬКО JSON:
{{
  "image_kind": "packshot|on_model|detail|bottle_label|lifestyle|unclear",
  "ocr_labels": ["короткие надписи"],
  "skip_reason": null или "почему почти ничего нельзя добавить",
  "new_attributes": [
    {{"name": "человекочитаемое имя", "value": "...", "evidence": "ocr|visual", "search_relevance": "high|medium|low", "filter_candidate": true}}
  ],
  "already_in_feed_visible": ["что видно но уже есть в фиде"],
  "not_useful_from_image": ["что видно но бесполезно для поиска"]
}}
Если new_attributes пустой — нормально. Не выдумывай."""


def call_openrouter(api_key: str, prompt: str, image_url: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/local/attr-enrichment-product",
        "X-Title": "TSUM vision gap probe",
    }
    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 1400,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=180)
    data = r.json()
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}", "raw": data}
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return {"error": "bad response shape", "raw": data}
    return {"raw_text": text, "usage": data.get("usage")}


def parse_json_content(text: str) -> dict:
    if not text:
        return {}
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m2 = re.search(r"\{[\s\S]*\}", text)
        if m2:
            try:
                return json.loads(m2.group(0))
            except json.JSONDecodeError:
                pass
    return {"parse_error": True, "raw_text": text[:2000]}


def main() -> None:
    api_key = load_api_key()
    by_bucket = json.loads(CAND.read_text(encoding="utf-8"))
    samples = pick_samples(by_bucket, MAX_PRODUCTS)
    print(f"model={MODEL} n={len(samples)}")

    results = []
    attr_counter: dict[str, int] = {}
    for i, p in enumerate(samples, 1):
        print(f"[{i}/{len(samples)}] {p.get('bucket')} :: {(p.get('name') or '')[:70]}")
        prompt = build_prompt(p)
        t0 = time.time()
        pic = p.get("picture") or (p.get("pictures") or [None])[0]
        if not pic:
            results.append({"product": p, "error": "no picture"})
            continue
        resp = call_openrouter(api_key, prompt, pic)
        elapsed = round(time.time() - t0, 2)
        if "error" in resp:
            print("  ERROR", resp["error"])
            results.append({"product": p, "error": resp, "elapsed_s": elapsed})
            continue
        parsed = parse_json_content(resp.get("raw_text", ""))
        new_attrs = parsed.get("new_attributes") or []
        for a in new_attrs:
            name = (a.get("name") or "").strip()
            if name:
                attr_counter[name] = attr_counter.get(name, 0) + 1
        print(
            f"  kind={parsed.get('image_kind')} new={len(new_attrs)} "
            f"ocr={len(parsed.get('ocr_labels') or [])} {elapsed}s"
        )
        results.append(
            {
                "product": {
                    "offer_id": p.get("offer_id"),
                    "name": p.get("name"),
                    "bucket": p.get("bucket"),
                    "category_name": p.get("category_name"),
                    "vendor": p.get("vendor"),
                    "picture": pic,
                    "url": p.get("url"),
                    "params_keys": list((p.get("params") or {}).keys()),
                },
                "model": MODEL,
                "elapsed_s": elapsed,
                "usage": resp.get("usage"),
                "vision": parsed,
            }
        )
        time.sleep(0.35)

    summary = {
        "site_id": 203,
        "partner": "TSUM",
        "model": MODEL,
        "n_probed": len(results),
        "attr_name_hits": sorted(attr_counter.items(), key=lambda x: -x[1]),
        "with_new_attrs": sum(
            1 for r in results if (r.get("vision") or {}).get("new_attributes")
        ),
        "empty_new": sum(
            1
            for r in results
            if "error" not in r and not (r.get("vision") or {}).get("new_attributes")
        ),
        "errors": sum(1 for r in results if "error" in r),
    }
    out_path = OUT / "vision_probe_results.json"
    out_path.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "vision_probe_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Wrote", out_path)


if __name__ == "__main__":
    main()
