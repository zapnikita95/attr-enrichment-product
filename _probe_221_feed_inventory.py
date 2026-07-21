# -*- coding: utf-8 -*-
"""Inventory site 221 from feed.db + gold CSV (semicolon) + sample for vision."""
from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "portfolio" / "221_azbuka"
OUT.mkdir(parents=True, exist_ok=True)

AE = Path(r"C:\Users\1\OneDrive\Desktop\attributes_extraction-main\data\projects\221")
GOLD_CSV = Path(r"C:\Users\1\OneDrive\Desktop\221_azbuka_vkusa_gold_final_20260721_0958.csv")
FEED_DB = AE / "feed.db"

# Skip noisy / non-searchable feed params (ops, promo, nutrition macros often already indexed)
SKIP_PARAM_PREFIXES = ()
SKIP_PARAM_EXACT = {
    "currencyId",
    "dimension22",
    "id",
    "name",
    "nonprice_promo",
    "only_for_eighteen_plus",
    "picture",
    "price",
    "price_promo",
    "promo_id",
    "promo_name",
    "sales_notes",
    "store",
    "typePrefix",
    "usp",
    "url",
    "categoryId",
    "market_category",
    "margin",
}


def load_gold() -> tuple[dict[str, list[tuple[str, str]]], Counter]:
    by: dict[str, list[tuple[str, str]]] = defaultdict(list)
    names: Counter = Counter()
    with GOLD_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            oid = (row.get("offer_id") or "").strip()
            status = (row.get("status") or "").strip()
            raw = (row.get("attributes") or "").strip()
            if not oid or not raw or status == "empty":
                continue
            # attributes often like name=value | name=value OR JSON
            attrs: list[tuple[str, str]] = []
            if raw.startswith("{") or raw.startswith("["):
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if v is None:
                                continue
                            if isinstance(v, list):
                                v = ", ".join(str(x) for x in v)
                            attrs.append((str(k).strip(), str(v).strip()))
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                an = item.get("name") or item.get("attribute_name")
                                av = item.get("value") or item.get("attribute_value")
                                if an and av is not None:
                                    attrs.append((str(an).strip(), str(av).strip()))
                except json.JSONDecodeError:
                    pass
            if not attrs:
                # pipe / semicolon separated pairs
                parts = [p.strip() for p in raw.replace("||", "|").split("|") if p.strip()]
                for p in parts:
                    if "=" in p:
                        an, av = p.split("=", 1)
                        attrs.append((an.strip(), av.strip()))
                    elif ":" in p:
                        an, av = p.split(":", 1)
                        attrs.append((an.strip(), av.strip()))
            for an, av in attrs:
                if an and av:
                    by[oid].append((an, av))
                    names[an] += 1
    return by, names


def main():
    gold, gold_names = load_gold()
    print(f"gold offers with attrs: {len(gold)} unique attr names: {len(gold_names)}")
    print("top gold:", gold_names.most_common(20))

    con = sqlite3.connect(str(FEED_DB))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    n = cur.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
    print("offers in db:", n)

    param_names = Counter()
    type_counts = Counter()
    path_counts = Counter()
    with_pic = 0
    samples_by_type: dict[str, list[dict]] = defaultdict(list)

    rows = cur.execute(
        "SELECT id, name, description, params_json, market_category, feed_category_id, "
        "product_type, feed_category_path FROM offers"
    )
    for row in rows:
        oid = row["id"]
        ptype = row["product_type"] or "other"
        type_counts[ptype] += 1
        path = row["feed_category_path"] or ""
        if path:
            # L1
            l1 = path.split(" / ")[0].strip()
            path_counts[l1] += 1
        try:
            params = json.loads(row["params_json"] or "{}")
        except json.JSONDecodeError:
            params = {}
        pic = (params.get("picture") or "").strip()
        if pic:
            with_pic += 1
        for k in params:
            if k in SKIP_PARAM_EXACT:
                continue
            param_names[k] += 1

        # keep samples for top food types
        if pic and len(samples_by_type[ptype]) < 5:
            ga = gold.get(str(oid), [])
            # searchable params only
            clean_params = {
                k: v
                for k, v in params.items()
                if k not in SKIP_PARAM_EXACT and v not in (None, "", "0")
            }
            samples_by_type[ptype].append(
                {
                    "id": str(oid),
                    "name": row["name"] or "",
                    "product_type": ptype,
                    "feed_category_id": row["feed_category_id"] or "",
                    "feed_category_path": path,
                    "market_category": row["market_category"] or "",
                    "picture": pic,
                    "description": (row["description"] or "")[:500],
                    "params": clean_params,
                    "gold_attrs": [{"name": a, "value": v} for a, v in ga[:50]],
                    "gold_attr_names": sorted({a for a, _ in ga}),
                    "has_gold": bool(ga),
                }
            )

    # Focus food product types from gold summary
    focus_types = [
        "food_meat_products",
        "milk_products",
        "food_beverages_non_alcohol",
        "bakery_dairy",
        "food_fruits_vegetables",
        "food_beverages_alcohol",
        "food_products",
        "food_desserts_cakes",
        "bakery_breads_pastries",
        "meat_and_fish_products",
        "condiments_oils_spices_sauces",
        "bakery_and_sweets",
        "grains_and_legumes",
        "snacks_and_chips",
        "alcohol_and_wine",
        "beverages_alcohol_spirits_liqueurs",
        "pet_food_wet_dry",
        "canned_fruits_vegetables_delicacies",
        "cheeses_blue_ripened",
        "pates_liver_meat",
        "frozen_dishes_pancakes_meat",
        "sauces_mayonnaise_creamy",
        "seafood_frozen_raw",
    ]

    vision_candidates = []
    for pt in focus_types:
        for s in samples_by_type.get(pt, [])[:3]:
            vision_candidates.append(s)
    # fill from other types if short
    if len(vision_candidates) < 40:
        for pt, lst in samples_by_type.items():
            if pt in focus_types:
                continue
            for s in lst[:1]:
                vision_candidates.append(s)
            if len(vision_candidates) >= 50:
                break

    out = {
        "site_id": 221,
        "partner": "Азбука Вкуса",
        "offers_total": n,
        "with_picture": with_pic,
        "picture_pct": round(100 * with_pic / n, 2) if n else 0,
        "gold_offers_with_attrs": len(gold),
        "gold_unique_attr_names": len(gold_names),
        "gold_top_attrs": gold_names.most_common(80),
        "yml_param_names_searchable": param_names.most_common(80),
        "product_type_counts": type_counts.most_common(40),
        "l1_path_counts": path_counts.most_common(30),
        "focus_types": focus_types,
        "samples_by_type": {k: v for k, v in samples_by_type.items() if k in focus_types or k in dict(type_counts.most_common(15))},
    }
    (OUT / "feed_inventory.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "vision_candidates.json").write_text(
        json.dumps(vision_candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "gold_attr_names.json").write_text(
        json.dumps(gold_names.most_common(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"with_pic={with_pic}/{n} gold_offers={len(gold)} candidates={len(vision_candidates)}"
    )
    print("L1:", path_counts.most_common(15))
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
