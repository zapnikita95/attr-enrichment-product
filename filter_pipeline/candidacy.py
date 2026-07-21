"""LLM: which attributes can be Diginetica filters (vs search-only / reject)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .llm_client import DEFAULT_TEXT_MODEL, chat_text, parse_json_object

SYSTEM = (
    "Ты product analyst Diginetica (fashion e-commerce filters). "
    "Отвечай только валидным JSON без markdown."
)

PROMPT = """Партнёр: Zolla (одежда). Нужно решить, какие атрибуты подходят как **FACET-ФИЛЬТРЫ** в поиске/каталоге.

Правила фильтра:
- низкая/средняя кардинальность (boolean или ≤12 значений)
- понятен покупателю как галочка/чипсы
- значение стабильно нормализуется (не свободный текст)
- НЕ фильтр: маркетинговый fluff, ощущения ткани, редкие уникальные фразы, уже размер/цена/бренд из фида

Кандидаты (имя + примеры значений из extract):
{candidates_json}

Категории фокуса: {categories}

Верни JSON:
{{
  "decisions": [
    {{
      "name": "...",
      "role": "filter" | "search_only" | "reject",
      "why": "1-2 предложения мотивация",
      "suggested_value_type": "boolean" | "enum" | "multi_enum" | "numeric_bins" | null,
      "suggested_cardinality": "2" | "3-7" | "8-12" | "high" | null
    }}
  ]
}}
"""


def run_candidacy(
    candidates: list[dict[str, Any]],
    *,
    categories: list[str],
    model: str = DEFAULT_TEXT_MODEL,
    out_path: Path | None = None,
) -> dict[str, Any]:
    prompt = PROMPT.format(
        candidates_json=json.dumps(candidates, ensure_ascii=False, indent=2),
        categories=", ".join(categories),
    )
    raw = chat_text(prompt, system=SYSTEM, model=model, max_tokens=2500)
    parsed = parse_json_object(raw)
    result = {
        "model": model,
        "categories": categories,
        "candidates_in": candidates,
        "raw_text": raw,
        "parsed": parsed,
    }
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
