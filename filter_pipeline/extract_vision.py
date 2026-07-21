"""Closed-set vision extract: ONE filter attribute per call."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .coerce import coerce_value
from .llm_client import DEFAULT_VISION_MODEL, chat_vision, parse_json_object
from .models import FilterAttributeSpec

LUREX_VERIFY_MODEL = "google/gemini-2.5-flash-lite"
LUREX_VERIFY_PROMPT = """На фото трикотаж/одежда. Есть ли металлический блеск нитей (люрекс: серебро/золото)?
Меланж (матовая смесь цветов без металла) — это НЕ люрекс.
Ответ только JSON: {"has_lurex": true/false, "confidence": 0-100}"""

SYSTEM = (
    "Ты vision-экстрактор facet-фильтров для fashion. "
    "Отвечай ТОЛЬКО JSON. Значение — строго из allowed_values, без пояснений в value."
)


def build_prompt(spec: FilterAttributeSpec, product_name: str = "") -> str:
    allowed = json.dumps(spec.allowed_values, ensure_ascii=False)
    if spec.value_type == "boolean":
        value_rule = (
            'value — ровно одно из allowed_values: "да" или "нет". '
            "Запрещено писать «есть», «капюшон», «с капюшоном», «присутствует». "
            "Для капюшона: да = капюшон виден (на голове, сзади, сложен/опущен на спине, меховая опушка у горловины). "
            "нет = обычный воротник/капюшона нет. Не путай капюшон с воротником-стойкой или шарфом."
        )
    elif spec.multi:
        value_rule = (
            "value — строка из одного канона ИЛИ массив канонов из allowed_values. "
            "Не добавляй слова вне списка. Если узора нет — «однотонный»."
        )
        if spec.attr_id == "print_pattern":
            value_rule += (
                "\nЛюрекс vs меланж: люрекс = заметные металлические/блестящие нити (серебро/золото) в вязке; "
                "меланж = матовая смесь цветов пряжи без металлического блеска. "
                "Гусиная лапка = только геометрическая pied-de-poule, не леопард и не праздничная графика. "
                "Название товара может врать про люрекс — верь фото."
            )
    else:
        value_rule = "value — ровно ОДНО значение из allowed_values. Никаких свободных фраз."

    return f"""Атрибут-фильтр: {spec.label_ru} (id={spec.attr_id})
Тип: {spec.value_type}
allowed_values: {allowed}
Товар (подсказка, не источник истины): {product_name or "—"}

Смотри ТОЛЬКО фото. {value_rule}
Если не уверен — выбери наиболее вероятный канон и понизь confidence.

JSON:
{{
  "attr_id": "{spec.attr_id}",
  "value": ...,
  "confidence": 0-100,
  "evidence": "коротко что видно"
}}
"""


def extract_one(
    spec: FilterAttributeSpec,
    sample: dict[str, Any],
    *,
    model: str = DEFAULT_VISION_MODEL,
) -> dict[str, Any]:
    prompt = build_prompt(spec, sample.get("name") or "")
    local = sample.get("local_image")
    url = sample.get("picture_url") or ""
    t0 = time.time()
    err = None
    raw_text = ""
    try:
        if local and Path(local).is_file():
            raw_text = chat_vision(prompt, image_path=Path(local), system=SYSTEM, model=model)
        elif url:
            raw_text = chat_vision(prompt, image_url=url, system=SYSTEM, model=model)
        else:
            raise RuntimeError("no image")
    except Exception as e:
        err = str(e)
    elapsed = round(time.time() - t0, 2)
    parsed = parse_json_object(raw_text) if raw_text else {}
    raw_val = parsed.get("value")
    coerced = coerce_value(spec, raw_val)
    lurex_verify = None

    # Second pass: flash-lite lurex check when primary said melange/solid
    if (
        not err
        and spec.attr_id == "print_pattern"
        and coerced.ok
        and str(coerced.value) in {"меланж", "однотонный"}
    ):
        try:
            if local and Path(local).is_file():
                vraw = chat_vision(
                    LUREX_VERIFY_PROMPT,
                    image_path=Path(local),
                    model=LUREX_VERIFY_MODEL,
                    max_tokens=128,
                )
            elif url:
                vraw = chat_vision(
                    LUREX_VERIFY_PROMPT,
                    image_url=url,
                    model=LUREX_VERIFY_MODEL,
                    max_tokens=128,
                )
            else:
                vraw = ""
            vparsed = parse_json_object(vraw)
            lurex_verify = {"model": LUREX_VERIFY_MODEL, "parsed": vparsed, "raw": vraw}
            if vparsed.get("has_lurex") is True and int(vparsed.get("confidence") or 0) >= 60:
                coerced = coerce_value(spec, "люрекс")
                raw_val = f"{raw_val}+lurex_verify"
        except Exception as e:
            lurex_verify = {"error": str(e)}

    expected = sample.get("expected")
    match_expected = None
    if expected is not None and coerced.ok:
        if isinstance(coerced.value, list):
            match_expected = expected in coerced.value or any(
                expected in str(v) for v in coerced.value
            )
        else:
            match_expected = str(coerced.value) == str(expected) or str(expected) in str(
                coerced.value
            )

    return {
        "offer_id": sample.get("offer_id"),
        "name": sample.get("name"),
        "attr_id": spec.attr_id,
        "model": model,
        "elapsed_s": elapsed,
        "error": err,
        "raw_text": raw_text,
        "parsed": parsed,
        "raw_value": raw_val,
        "coerced_ok": coerced.ok,
        "coerced_value": coerced.value,
        "coerce_reason": coerced.reason,
        "mapped_from": coerced.mapped_from,
        "lurex_verify": lurex_verify,
        "expected": expected,
        "match_expected": match_expected,
        "confidence": parsed.get("confidence"),
        "evidence": parsed.get("evidence"),
        "local_image": local,
        "picture_url": url,
    }


def run_extract_batch(
    spec: FilterAttributeSpec,
    samples: list[dict[str, Any]],
    *,
    model: str = DEFAULT_VISION_MODEL,
    out_path: Path | None = None,
) -> dict[str, Any]:
    rows = []
    for i, s in enumerate(samples, 1):
        print(f"  [{i}/{len(samples)}] {s.get('offer_id')} {(s.get('name') or '')[:50]}")
        row = extract_one(spec, s, model=model)
        status = "OK" if row["coerced_ok"] else f"FAIL:{row.get('coerce_reason') or row.get('error')}"
        print(
            f"    raw={row.get('raw_value')!r} → {row.get('coerced_value')!r} "
            f"exp={row.get('expected')!r} {status} {row['elapsed_s']}s"
        )
        rows.append(row)

    n = len(rows)
    coerced_ok = sum(1 for r in rows if r["coerced_ok"])
    with_exp = [r for r in rows if r.get("expected") is not None and r["coerced_ok"]]
    match_n = sum(1 for r in with_exp if r.get("match_expected"))
    summary = {
        "attr_id": spec.attr_id,
        "model": model,
        "n": n,
        "coerced_ok": coerced_ok,
        "coerced_rate": round(coerced_ok / n, 3) if n else 0,
        "expected_n": len(with_exp),
        "expected_match": match_n,
        "expected_match_rate": round(match_n / len(with_exp), 3) if with_exp else None,
        "ood_or_fail": n - coerced_ok,
        "rows": rows,
    }
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
