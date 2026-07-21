# -*- coding: utf-8 -*-
import json
from pathlib import Path

p = Path(__file__).resolve().parent / "portfolio" / "221_azbuka" / "vision_probe_results.json"
data = json.loads(p.read_text(encoding="utf-8"))

SKIP_SUB = [
    "белк",
    "жир",
    "углевод",
    "энергет",
    "срок год",
    "кбжу",
    "история бренда",
    "производитель",
    "бренд",
    "ту",
    "регион производ",
    "апелласьон",  # often already in feed/name for wine
]


def skip_name(n: str) -> bool:
    nl = (n or "").lower()
    return any(x in nl for x in SKIP_SUB)


rows = []
for r in data["results"]:
    v = r.get("vision") or {}
    new = v.get("new_attributes") or []
    kept = [a for a in new if not skip_name(a.get("name", ""))]
    # also drop if value already in product name
    name_l = (r["product"]["name"] or "").lower()
    kept2 = []
    for a in kept:
        val = str(a.get("value") or "").lower()
        if val and val in name_l:
            continue
        # flavor tokens often in name
        if a.get("name", "").lower() in {"вкус", "вкус/наполнитель"} and any(
            tok in name_l for tok in val.replace(",", " ").split() if len(tok) > 3
        ):
            continue
        kept2.append(a)
    rows.append(
        {
            "id": r["product"]["id"],
            "type": r["product"]["product_type"],
            "path": r["product"]["feed_category_path"],
            "kind": v.get("image_kind"),
            "name": r["product"]["name"],
            "raw_n": len(new),
            "kept": kept2,
            "ocr_n": len(v.get("ocr_labels") or []),
            "skip_reason": v.get("skip_reason"),
        }
    )

out = Path(__file__).resolve().parent / "portfolio" / "221_azbuka" / "vision_probe_filtered.json"
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
for row in rows:
    print(
        f"{row['type']:35} kind={str(row['kind']):22} kept={len(row['kept'])} ocr={row['ocr_n']}"
    )
    for a in row["kept"]:
        print(f"   + {a.get('name')}={a.get('value')} [{a.get('search_relevance')}]")
print("wrote", out)
