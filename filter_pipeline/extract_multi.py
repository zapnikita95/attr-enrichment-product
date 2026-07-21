"""One vision call → all filter attrs for a product (max filters per photo)."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .coerce import coerce_value, feed_collision
from .llm_client import DEFAULT_VISION_MODEL, chat_vision, parse_json_object, vision_model_for_attr
from .models import FASHION_SEED_SPECS, FilterAttributeSpec
from .schema_stage import load_specs

SYSTEM = (
    "Ты vision-экстрактор facet-фильтров fashion. "
    "С одного фото достаёшь МАКСИМУМ атрибутов из схемы. "
    "Ответ — только JSON. Значения строго из allowed_values каждого атрибута."
)

# Collar: crew/round ≠ отложной (polo/shirt collar)
COLLAR_HINT = (
    "воротник/вырез: круглый = crew/обычный круглый вырез футболки; "
    "отложной = рубашечный/поло отворот; стойка = гольф/водолазка; "
    "V-образный = V-вырез. НЕ называй круглый вырез «отложной»."
)


def _specs(schema_path: Path | None = None) -> list[FilterAttributeSpec]:
    if schema_path and schema_path.is_file():
        specs = load_specs(schema_path)
        by = {s.attr_id: s for s in specs}
        for seed in FASHION_SEED_SPECS:
            if seed.attr_id in by:
                syn = dict(seed.synonym_map)
                syn.update(by[seed.attr_id].synonym_map or {})
                by[seed.attr_id].synonym_map = syn
                if not by[seed.attr_id].allowed_values:
                    by[seed.attr_id].allowed_values = list(seed.allowed_values)
            else:
                by[seed.attr_id] = seed
        # extra filter candidates visible on many Zolla cards
        extras = [
            FilterAttributeSpec(
                attr_id="belt_drawstring",
                label_ru="Пояс / кулиска",
                value_type="boolean",
                allowed_values=["да", "нет"],
                why_filter="Наличие пояса или кулиски — бинарная деталь.",
                synonym_map={"с поясом": "да", "на кулиске": "да", "кулиска": "да", "пояс": "да"},
            ),
            FilterAttributeSpec(
                attr_id="quilted",
                label_ru="Стёганый",
                value_type="boolean",
                allowed_values=["да", "нет"],
                why_filter="Стёжка/quilting видна на фото верхней одежды.",
                synonym_map={"стёганый": "да", "стеганый": "да", "quilted": "да"},
            ),
        ]
        for e in extras:
            by.setdefault(e.attr_id, e)
        return list(by.values())
    return list(FASHION_SEED_SPECS)


def build_multi_prompt(specs: list[FilterAttributeSpec], product_name: str = "") -> str:
    schema_lines = []
    for s in specs:
        schema_lines.append(
            f"- {s.attr_id} ({s.label_ru}, {s.value_type}): allowed={json.dumps(s.allowed_values, ensure_ascii=False)}"
        )
    schema_block = "\n".join(schema_lines)
    return f"""На фото товар одежды. Достань ВСЕ атрибуты-фильтры из схемы ниже, которые видно на фото.
Если атрибут не применим / не видно — всё равно поставь лучший канон (для boolean часто «нет»).

Схема:
{schema_block}

Правила:
- value ТОЛЬКО из allowed_values соответствующего attr_id
- Смотри ТОЛЬКО основное изделие из названия товара. Игнорь обувь, сумки и второй слой аутфита
  (водолазка под юбкой, брюки под футболкой) — их рукава/воротник НЕ атрибуты главного SKU.
- {COLLAR_HINT}
- капюшон: да только если капюшон реально виден на главном изделии
- length: длина ГЛАВНОГО изделия (mini/midi/maxi/до колена/укороченный); для футболок/топов — укороченный или midi по крою
- sleeve_length: рукава ГЛАВНОГО изделия; для юбки/брюк без верха — не выдумывай (если юбка — можно опустить смысл, ставь null в evidence и value «без рукавов» только для топов без рукавов)
- fastener: молния/пуговицы/кнопки/завязки/нет — ОСНОВНАЯ застёжка борта/переда изделия.
  Пояс, кулиска, бант на талии → ТОЛЬКО belt_drawstring=да, НЕ fastener=завязки.
  завязки — только если изделие держится/застёгивается завязками как халат/кимоно без молнии/пуговиц.
- belt_drawstring: да если есть пояс, ремень, кулиска или бант-завязка на изделии
- quilted: да если видна стёжка утеплителя на верхней одежде
- Не выдумывай материал-состав % (это не из этой схемы)

Товар (подсказка): {product_name or "—"}

JSON:
{{
  "attributes": [
    {{"attr_id": "...", "value": ..., "confidence": 0-100, "evidence": "что видно"}}
  ]
}}
"""


def _norm_blob(*parts: str) -> str:
    return " ".join(re.sub(r"\s+", " ", (p or "").lower().replace("ё", "е")) for p in parts)


def _stem_close(a: str, b: str) -> bool:
    """полоски↔полоска, однотонный↔однотон."""
    a, b = a.strip(), b.strip()
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    for x, y in ((a, b), (b, a)):
        if len(x) >= 4 and x.rstrip("иыая") and x.rstrip("иыая") in y:
            return True
    return False


def classify_vs_feed(
    attr_id: str,
    value: Any,
    *,
    product_name: str,
    old_extract: dict[str, str],
) -> str:
    """Return keep | mention_in_title | collision_old_extract | empty.

    Title mention ≠ feed collision for filters: «капюшон» в name всё ещё
    нужен как structured facet. Collision только если уже был в старом extract.
    """
    v = value[0] if isinstance(value, list) and value else value
    vs = str(v or "").strip().lower().replace("ё", "е")
    if not vs:
        return "empty"

    old_map = {str(k).lower(): str(val).lower().replace("ё", "е") for k, val in (old_extract or {}).items()}
    old = old_map.get(attr_id) or ""
    if attr_id == "print_pattern" and not old:
        old = old_map.get("print_pattern") or old_map.get("принт") or ""
    # clothing.* freeform keys from results.db
    if not old and attr_id == "print_pattern":
        for k, val in old_map.items():
            if "print" in k or "принт" in k or "узор" in k:
                old = val
                break
    if old and _stem_close(vs, old):
        return "collision_old_extract"

    # Color / size style collisions via shared helper (short tokens skipped)
    if attr_id in {"print_pattern", "length"} and feed_collision(str(v), product_name):
        # mini/maxi in title → still keep as facet (title is not a filter UI)
        if attr_id == "length":
            return "mention_in_title"
        return "collision_old_extract" if old else "mention_in_title"

    name_l = (product_name or "").lower().replace("ё", "е")
    title_markers = {
        "hood": ("капюшон",),
        "belt_drawstring": ("пояс", "кулиск", "завяз", "бант"),
        "fastener": ("молни", "пуговиц", "завяз"),
        "length": ("мини", "миди", "макси", "mini", "midi", "maxi"),
        "quilted": ("стеган", "стёган", "утепл"),
        "sleeve_length": ("без рукав", "короткий рукав", "длинный рукав"),
    }
    for marker in title_markers.get(attr_id, ()):
        if marker in name_l and vs in {"да", "mini", "midi", "maxi", "молния", "завязки", "без рукавов"}:
            return "mention_in_title"
    return "keep"


def extract_all_filters(
    sample: dict[str, Any],
    specs: list[FilterAttributeSpec],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    model = model or vision_model_for_attr("print_pattern")  # flash-lite mid quality for multi
    # prefer flash-lite for multi-attr quality on budget
    if not model or "gemma" in model:
        model = "google/gemini-2.5-flash-lite"
    prompt = build_multi_prompt(specs, sample.get("name") or "")
    local = sample.get("local_image")
    url = sample.get("picture_url") or ""
    t0 = time.time()
    err = None
    raw = ""
    parsed: dict[str, Any] = {}
    for attempt in range(3):
        try:
            if local and Path(local).is_file():
                raw = chat_vision(prompt, image_path=Path(local), system=SYSTEM, model=model, max_tokens=1200)
            elif url:
                raw = chat_vision(prompt, image_url=url, system=SYSTEM, model=model, max_tokens=1200)
            else:
                raise RuntimeError("no image")
            parsed = parse_json_object(raw) if raw else {}
            if parsed.get("attributes"):
                err = None
                break
            err = f"empty_attributes_attempt_{attempt+1}"
        except Exception as e:
            err = str(e)
            parsed = {}
        time.sleep(0.8 * (attempt + 1))
    elapsed = round(time.time() - t0, 2)
    by_id = {s.attr_id: s for s in specs}
    old_extract = sample.get("old_extract") or {}
    name = sample.get("name") or ""

    rows = []
    for item in parsed.get("attributes") or []:
        if not isinstance(item, dict):
            continue
        aid = str(item.get("attr_id") or "").strip()
        if aid not in by_id:
            continue
        spec = by_id[aid]
        c = coerce_value(spec, item.get("value"))
        status = "ood"
        if c.ok:
            status = classify_vs_feed(aid, c.value, product_name=name, old_extract=old_extract)
        rows.append(
            {
                "attr_id": aid,
                "label": spec.label_ru,
                "value_type": spec.value_type,
                "raw_value": item.get("value"),
                "coerced_ok": c.ok,
                "coerced_value": c.value,
                "confidence": item.get("confidence"),
                "evidence": item.get("evidence"),
                "status": status if c.ok else (c.reason or "ood"),
                "filter_ui": f"{spec.label_ru} = {c.value}" if c.ok else None,
            }
        )

    # ensure all schema keys appear (missing → note)
    have = {r["attr_id"] for r in rows}
    for s in specs:
        if s.attr_id not in have:
            rows.append(
                {
                    "attr_id": s.attr_id,
                    "label": s.label_ru,
                    "value_type": s.value_type,
                    "raw_value": None,
                    "coerced_ok": False,
                    "coerced_value": None,
                    "status": "not_returned",
                    "filter_ui": None,
                }
            )

    keep = [r for r in rows if r.get("status") == "keep"]
    collision = [r for r in rows if str(r.get("status", "")).startswith("collision")]
    return {
        "offer_id": sample.get("offer_id"),
        "name": name,
        "picture_url": url,
        "local_image": local,
        "model": model,
        "elapsed_s": elapsed,
        "error": err,
        "raw_text": raw,
        "attributes": rows,
        "keep_new_filters": keep,
        "collisions": collision,
        "keep_count": len(keep),
    }
