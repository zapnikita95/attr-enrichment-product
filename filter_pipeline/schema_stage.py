"""LLM: value_type + closed allowed_values for filter attributes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .llm_client import DEFAULT_TEXT_MODEL, chat_text, parse_json_object
from .models import FASHION_SEED_SPECS, FilterAttributeSpec

SYSTEM = (
    "Ты schema designer для facet-фильтров fashion. "
    "Жёсткая нормализация: allowed_values — канон, без синонимов внутри списка. "
    "Ответ — только JSON."
)

PROMPT = """Спроектируй filter_schema для партнёра Zolla (одежда).

Атрибуты на схему (уже прошли filter candidacy или seed):
{attrs_json}

Требования:
1. value_type: boolean | enum | multi_enum | numeric_bins
2. boolean → allowed_values ТОЛЬКО ["да","нет"] (русский)
3. enum/multi_enum → 2..12 значений, короткие RU/латиница-канон (mini/midi/maxi ок)
4. synonym_map: частые отклонения модели → канон (чтобы «капюшон есть»→«да»)
5. categories: где фильтр релевантен
6. why_filter: зачем facet

Верни JSON:
{{
  "attributes": [
    {{
      "attr_id": "snake_case_en",
      "label_ru": "...",
      "value_type": "...",
      "allowed_values": ["..."],
      "multi": false,
      "categories": ["..."],
      "why_filter": "...",
      "synonym_map": {{"синоним": "канон"}},
      "dashboard_attr": "digi_filter_..."
    }}
  ]
}}
"""


def seed_attrs_payload() -> list[dict[str, Any]]:
    return [
        {
            "attr_id": s.attr_id,
            "label_ru": s.label_ru,
            "hint_type": s.value_type,
            "seed_allowed": s.allowed_values,
            "why_filter": s.why_filter,
        }
        for s in FASHION_SEED_SPECS
    ]


def run_schema_stage(
    attrs: list[dict[str, Any]] | None = None,
    *,
    model: str = DEFAULT_TEXT_MODEL,
    out_path: Path | None = None,
    merge_seed: bool = True,
) -> dict[str, Any]:
    payload = attrs if attrs is not None else seed_attrs_payload()
    prompt = PROMPT.format(attrs_json=json.dumps(payload, ensure_ascii=False, indent=2))
    raw = chat_text(prompt, system=SYSTEM, model=model, max_tokens=3000)
    parsed = parse_json_object(raw)
    specs: list[FilterAttributeSpec] = []
    for item in parsed.get("attributes") or []:
        if not isinstance(item, dict):
            continue
        try:
            specs.append(FilterAttributeSpec.from_dict(item))
        except Exception:
            continue

    # Ensure pilot attrs exist even if LLM skipped them
    if merge_seed:
        have = {s.attr_id for s in specs}
        for s in FASHION_SEED_SPECS:
            if s.attr_id not in have:
                specs.append(s)

    schema = {
        "model": model,
        "attributes": [s.to_dict() for s in specs if s.attr_id],
        "raw_text": raw,
        "parsed": parsed,
    }
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Persist clean schema without huge raw if wanted — keep full for audit
        out_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
        clean = {"attributes": schema["attributes"]}
        clean_path = out_path.with_name("filter_schema_clean.json")
        clean_path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    return schema


def load_specs(schema_path: Path) -> list[FilterAttributeSpec]:
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    attrs = data.get("attributes") or data
    if isinstance(attrs, dict):
        attrs = attrs.get("attributes") or []
    return [FilterAttributeSpec.from_dict(a) for a in attrs if isinstance(a, dict)]
