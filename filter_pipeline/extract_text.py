"""Map attributes_extraction Zolla gold/results onto filter_schema (coerce only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .coerce import coerce_value, feed_collision
from .models import FilterAttributeSpec

GOLD_DIR = Path(r"C:\Users\1\OneDrive\Desktop\attributes_extraction-main\data\projects\3826")

# Rough name aliases gold → filter attr_id
NAME_ALIASES: dict[str, str] = {
    "длина изделия": "length",
    "длина изделия/особенности кроя": "length",
    "тип принта/узора": "print_pattern",
    "тип узора/фактуры": "print_pattern",
    "наличие карманов/деталей": "pockets",
    "капюшон": "hood",
}


def _iter_gold_rows(limit_files: int = 6) -> list[dict[str, Any]]:
    files = sorted(GOLD_DIR.glob("gold_extraction_*.json"))[:limit_files]
    rows: list[dict[str, Any]] = []
    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        # shapes vary: list of offers or dict with results
        items = data if isinstance(data, list) else data.get("results") or data.get("offers") or []
        if isinstance(data, dict) and not items:
            # sometimes {offer_id: {...}}
            if all(isinstance(v, dict) for v in data.values()):
                items = [{"offer_id": k, **v} for k, v in data.items() if k not in ("meta", "summary")]
        for it in items:
            if not isinstance(it, dict):
                continue
            rows.append({"_file": fp.name, **it})
    return rows


def _extract_attr_pairs(offer: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return (attr_name, value, product_name)."""
    name = str(offer.get("name") or offer.get("product_name") or "")
    pairs: list[tuple[str, str, str]] = []
    attrs = offer.get("attributes") or offer.get("extracted") or offer.get("values") or {}
    if isinstance(attrs, list):
        for a in attrs:
            if not isinstance(a, dict):
                continue
            an = str(a.get("name") or a.get("attribute") or "").strip()
            av = a.get("value")
            if an and av is not None:
                pairs.append((an, str(av), name))
    elif isinstance(attrs, dict):
        for an, av in attrs.items():
            if isinstance(av, dict):
                av = av.get("value")
            if av is not None:
                pairs.append((str(an), str(av), name))
    return pairs


def map_gold_to_filters(
    specs: list[FilterAttributeSpec],
    *,
    out_path: Path | None = None,
    max_rows: int = 200,
) -> dict[str, Any]:
    from .models import FASHION_SEED_SPECS

    by_id = {s.attr_id: s for s in specs}
    for seed in FASHION_SEED_SPECS:
        if seed.attr_id in by_id:
            syn = dict(seed.synonym_map)
            syn.update(by_id[seed.attr_id].synonym_map or {})
            by_id[seed.attr_id].synonym_map = syn
        else:
            by_id[seed.attr_id] = seed
    gold = _iter_gold_rows()
    mapped: list[dict[str, Any]] = []
    stats: dict[str, dict[str, int]] = {}

    for offer in gold:
        for an, av, pname in _extract_attr_pairs(offer):
            alias = NAME_ALIASES.get(an.lower().strip())
            if not alias or alias not in by_id:
                continue
            spec = by_id[alias]
            st = stats.setdefault(alias, {"seen": 0, "ok": 0, "collision": 0, "ood": 0})
            st["seen"] += 1
            if feed_collision(av, pname):
                st["collision"] += 1
                mapped.append(
                    {
                        "offer_id": offer.get("offer_id") or offer.get("id"),
                        "attr_id": alias,
                        "raw": av,
                        "coerced_ok": False,
                        "reason": "feed_collision",
                        "source_file": offer.get("_file"),
                    }
                )
                continue
            c = coerce_value(spec, av)
            if c.ok:
                st["ok"] += 1
            else:
                st["ood"] += 1
            mapped.append(
                {
                    "offer_id": offer.get("offer_id") or offer.get("id"),
                    "attr_id": alias,
                    "raw": av,
                    "coerced_ok": c.ok,
                    "coerced_value": c.value,
                    "reason": c.reason,
                    "mapped_from": c.mapped_from,
                    "product_name": pname,
                    "source_file": offer.get("_file"),
                }
            )
            if len(mapped) >= max_rows:
                break
        if len(mapped) >= max_rows:
            break

    result = {"stats": stats, "n_mapped": len(mapped), "rows": mapped, "gold_files_scanned": True}
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
