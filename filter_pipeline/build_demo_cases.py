#!/usr/bin/env python3
"""Assemble real Zolla demo cases (photo URL + feed vs filter attrs) for partner HTML."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "portfolio" / "zolla_filters"
ZOLLA_DB = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main\projects\Zolla\results.db")

LABELS = {
    "hood": "Капюшон",
    "length": "Длина изделия",
    "print_pattern": "Узор / принт",
    "sleeve_length": "Длина рукава",
    "fastener": "Застёжка",
    "collar": "Воротник / вырез",
    "pockets": "Карманы",
}


def load_vision_index() -> dict[str, dict]:
    """offer_id -> {attr_id: coerced_value, picture_url, name, evidence}"""
    by_offer: dict[str, dict] = {}
    for p in OUT.glob("vision_*.json"):
        if "unique" in p.name or "summary" in p.name or "compare" in p.name:
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for row in data.get("rows") or []:
            if row.get("propagated"):
                continue
            if not row.get("coerced_ok"):
                continue
            oid = str(row.get("offer_id") or "")
            if not oid:
                continue
            slot = by_offer.setdefault(
                oid,
                {
                    "offer_id": oid,
                    "name": row.get("name") or "",
                    "picture_url": row.get("picture_url") or "",
                    "filters": {},
                    "evidence": {},
                },
            )
            if row.get("picture_url"):
                slot["picture_url"] = row["picture_url"]
            if row.get("name"):
                slot["name"] = row["name"]
            aid = row.get("attr_id")
            if aid:
                slot["filters"][aid] = row.get("coerced_value")
                slot["evidence"][aid] = row.get("evidence") or "visual"
    return by_offer


def feed_side(offer_id: str) -> tuple[dict, str]:
    """What was already in results/feed-ish fields for the case card."""
    if not ZOLLA_DB.is_file():
        return {}, ""
    con = sqlite3.connect(str(ZOLLA_DB))
    row = con.execute(
        "SELECT name, category, picture_url, attributes_json FROM results WHERE offer_id=?",
        (offer_id,),
    ).fetchone()
    con.close()
    if not row:
        return {}, ""
    name, cat, pic, aj = row
    feed = {"Цвет / оттенок": "—", "Категория": cat or "—"}
    try:
        a = json.loads(aj or "{}")
        clothing = a.get("clothing") or {}
        for k, label in (
            ("color", "Цвет"),
            ("color_shade", "Оттенок"),
            ("print_pattern", "Принт (старый freeform)"),
            ("material", "Материал"),
        ):
            v = clothing.get(k)
            if isinstance(v, dict) and v.get("value"):
                feed[label] = v["value"]
    except Exception:
        pass
    # Explicit: no structured filter params in Zolla YML
    feed["Капюшон (param)"] = "нет в фиде"
    feed["Застёжка (param)"] = "нет в фиде"
    feed["Длина как facet"] = "нет в фиде"
    return feed, pic or ""


def pick_cases(index: dict[str, dict]) -> list[dict]:
    """Hand-pick diverse real SKUs that tell the filter story."""
    wanted = [
        ("31629", "hood", "Капюшон виден на фото → boolean-фильтр «да»."),
        ("177548", "print_pattern", "Полоска на футболке → multi_enum фильтр «полоска»."),
        ("42955", "length", "Мини-платье → enum-фильтр длины mini."),
        ("83302", "length", "Макси-платье → enum-фильтр длины maxi."),
        ("39070", "fastener", "Молния на юбке → enum-фильтр застёжки."),
        ("38537", "collar", "Воротник-стойка → enum-фильтр воротника."),
        ("39614", "pockets", "Накладные карманы на куртке → boolean «да»."),
        ("15873", "sleeve_length", "Без рукавов → enum «без рукавов»."),
    ]
    cases = []
    for i, (oid, focus, blurb) in enumerate(wanted, 1):
        slot = index.get(oid)
        if not slot or not slot.get("picture_url"):
            # try find any offer with this attr from samples
            continue
        feed, pic = feed_side(oid)
        if pic:
            slot["picture_url"] = pic
        filters_out = []
        for aid, val in (slot.get("filters") or {}).items():
            filters_out.append(
                {
                    "attr_id": aid,
                    "label": LABELS.get(aid, aid),
                    "value": val,
                    "filter_ui": f"{LABELS.get(aid, aid)} = {val}",
                    "evidence": slot.get("evidence", {}).get(aid) or "visual",
                    "focus": aid == focus,
                }
            )
        # ensure focus attr present
        if not any(f["attr_id"] == focus for f in filters_out):
            continue
        cases.append(
            {
                "n": i,
                "offer_id": oid,
                "name": slot.get("name") or oid,
                "picture_url": slot["picture_url"],
                "product_url": f"https://zolla.com/catalog/?q={oid}",
                "blurb": blurb,
                "focus_attr": focus,
                "feed": feed,
                "extracted_filters": filters_out,
            }
        )
    # renumber
    for i, c in enumerate(cases, 1):
        c["n"] = i
    return cases


def main() -> None:
    idx = load_vision_index()
    cases = pick_cases(idx)
    path = OUT / "demo_cases.json"
    path.write_text(
        json.dumps(
            {
                "partner": "Zolla",
                "site_id": 3826,
                "rule": "Every partner filter defense MUST include real picture + real extracted filter values",
                "cases": cases,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"cases={len(cases)} → {path}")
    for c in cases:
        print(c["n"], c["offer_id"], c["focus_attr"], c["name"][:50], c["picture_url"][-40:])


if __name__ == "__main__":
    main()
