# -*- coding: utf-8 -*-
"""
OpenRouter vision probe for site 221 (Азбука Вкуса).

For each sample product: send picture + exclude name/feed params/gold text attrs.
Ask model what NEW searchable attributes are visible on packaging/photo.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "portfolio" / "221_azbuka"
CAND = OUT / "vision_candidates.json"
ENV = Path(r"C:\Users\1\OneDrive\Desktop\attributes_extraction-main\.env")

# Prefer OCR-capable mid tier for grocery packaging
MODEL = os.environ.get("OR_VISION_MODEL", "google/gemini-2.5-flash-lite")
MAX_PRODUCTS = int(os.environ.get("OR_VISION_N", "18"))
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Diversify across these product_types (order = priority)
FOCUS_ORDER = [
    "food_meat_products",
    "milk_products",
    "food_beverages_non_alcohol",
    "bakery_dairy",
    "food_fruits_vegetables",
    "food_beverages_alcohol",
    "bakery_breads_pastries",
    "food_desserts_cakes",
    "condiments_oils_spices_sauces",
    "snacks_and_chips",
    "grains_and_legumes",
    "meat_and_fish_products",
    "alcohol_and_wine",
    "pet_food_wet_dry",
    "bakery_and_sweets",
    "canned_fruits_vegetables_delicacies",
]


def load_api_key() -> str:
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if key:
        return key
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("OPENROUTER_API_KEY="):
                return s.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("OPENROUTER_API_KEY not found")


def pick_samples(cands: list[dict], n: int) -> list[dict]:
    by_type: dict[str, list] = {}
    for c in cands:
        by_type.setdefault(c.get("product_type") or "other", []).append(c)
    picked = []
    # round-robin focus types
    while len(picked) < n:
        progressed = False
        for pt in FOCUS_ORDER:
            lst = by_type.get(pt) or []
            if lst:
                picked.append(lst.pop(0))
                progressed = True
                if len(picked) >= n:
                    break
        if not progressed:
            break
    return picked


def build_prompt(p: dict) -> str:
    gold = p.get("gold_attrs") or []
    gold_lines = [f"- {a['name']}: {a['value']}" for a in gold[:30]]
    params = p.get("params") or {}
    # drop nutrition macros / storage noise from "already have" for clarity, keep searchable
    keep_keys = [
        k
        for k in params
        if k
        not in {
            "Белки",
            "Жиры",
            "Углеводы",
            "Пищевая ценность",
            "Энергетическая ценность",
            "Сайт производителя",
            "Нормативные документы",
            "Дополнительный срок годности",
            "Гарантированный срок годности",
            "Содержание спирта",
        }
    ]
    param_lines = [f"- {k}: {params[k]}" for k in keep_keys[:25]]

    return f"""Ты анализируешь фото товара из продуктового ритейлера (Азбука Вкуса).

ЗАДАЧА: найти атрибуты, которые РЕАЛЬНО видны на фото/упаковке (OCR надписей, иконки, визуал),
и которых НЕТ в названии, параметрах фида и уже извлечённых текстовых атрибутах.

НЕ ИЗВЛЕКАЙ (даже если видно):
- бренд/vendor если уже в названии
- вес/объём/страна если уже в названии или params
- цену, штрихкод, артикул
- КБЖУ / пищевую ценность / срок годности / температуру хранения (это уже в фиде)
- вкусовые «ноты», «послевкусие», «характер вкуса» — это маркетинг из текста, не с фото
- догадки про вкус/запах без явной надписи на упаковке
- цвет упаковки ради декора (кроме если это ключевой атрибут товара, напр. цвет сыра)

ИЩИ В ПРИОРИТЕТЕ (только если явно на фото и НЕТ в списках ниже):
- маркировки: без глютена, без лактозы, organic/био, халяль, кошер, vegan/веган, постное
- способ обработки на этикетке: копчёный, вяленый, охлаждённый, замороженный, УВТ, фильтрованный
- форма выпуска/нарезка: нарезка, ломтики, кубики, фарш, филе, зерно помол
- вкус/наполнитель как LABEL (клубника, ваниль, BBQ) — только если написано на упаковке
- состав/ингредиенты на этикетке, если их нет в фиде
- тип упаковки если НЕ в params: стекло, жесть, tetra, дойпак
- для алкоголя: регион, виноград, выдержка, крепость если на этикетке и нет в фиде
- для сыров/колбас: жирность %, выдержка, тип молока — только с этикетки
- визуально очевидное: «с косточкой/без», цельный плод vs нарезка, цвет мякоти (только если помогает поиску)

НАЗВАНИЕ: {p.get('name')}
КАТЕГОРИЯ: {p.get('feed_category_path')} | type={p.get('product_type')}

УЖЕ В ФИДЕ (НЕ повторяй):
{chr(10).join(param_lines) if param_lines else '(пусто)'}

УЖЕ ИЗВЛЕЧЕНО ТЕКСТОМ / gold (НЕ повторяй, считай загруженным):
{chr(10).join(gold_lines) if gold_lines else '(нет)'}

Верни ТОЛЬКО JSON:
{{
  "image_kind": "packshot|product_only|packshot_with_label|lifestyle|unclear",
  "ocr_labels": ["короткие надписи с упаковки"],
  "skip_reason": null или "почему почти ничего нельзя добавить с фото",
  "new_attributes": [
    {{"name": "человекочитаемое имя", "value": "...", "evidence": "ocr|icon|visual", "search_relevance": "high|medium|low"}}
  ],
  "not_useful_from_image": ["что видно но бесполезно для поиска"]
}}
Если new_attributes пустой — это нормально. Не выдумывай."""


def call_openrouter(api_key: str, prompt: str, image_url: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/local/attr-enrichment-product",
        "X-Title": "221 azbuka vision gap probe",
    }
    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 1200,
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
    r = requests.post(API_URL, headers=headers, json=payload, timeout=120)
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
    # strip fences
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


def main():
    api_key = load_api_key()
    cands = json.loads(CAND.read_text(encoding="utf-8"))
    samples = pick_samples(cands, MAX_PRODUCTS)
    print(f"model={MODEL} n={len(samples)}")

    results = []
    attr_counter: dict[str, int] = {}
    for i, p in enumerate(samples, 1):
        print(f"[{i}/{len(samples)}] {p['id']} {p['product_type']} :: {p['name'][:60]}")
        prompt = build_prompt(p)
        t0 = time.time()
        resp = call_openrouter(api_key, prompt, p["picture"])
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
                    "id": p["id"],
                    "name": p["name"],
                    "product_type": p["product_type"],
                    "feed_category_path": p["feed_category_path"],
                    "picture": p["picture"],
                    "gold_attr_names": p.get("gold_attr_names") or [],
                    "has_gold": p.get("has_gold"),
                },
                "model": MODEL,
                "elapsed_s": elapsed,
                "usage": resp.get("usage"),
                "vision": parsed,
            }
        )
        time.sleep(0.4)

    summary = {
        "site_id": 221,
        "partner": "Азбука Вкуса",
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
