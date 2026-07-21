# -*- coding: utf-8 -*-
"""Pick 5 partner demo cases: picture + NEW attrs not in feed name/params."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"
PROBE = OUT / "vision_probe_results.json"
CAND = OUT / "vision_candidates.json"
DECISION = OUT / "vision_attr_decision.json"

# Prefer these offer_ids from overseer / screenshot
PREFERRED = [
    "11302590",  # костюм полоска
    "13839154",  # платье вырез-капля
    "13661940",  # сумка хобо
    "13846153",  # куртка капюшон
    "13594873",  # пальто клетка тартан
]


def main() -> None:
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    cands = json.loads(CAND.read_text(encoding="utf-8"))
    by_id = {}
    for items in cands.values():
        for it in items:
            by_id[str(it["offer_id"])] = it
    keep = {
        (r["offer_id"], r["attr"].casefold(), r["value"].casefold()): r
        for r in json.loads(DECISION.read_text(encoding="utf-8"))["keep"]
    }

    by_offer = {str(r["product"]["offer_id"]): r for r in probe["results"] if "product" in r}

    cases = []
    for oid in PREFERRED:
        r = by_offer.get(oid)
        full = by_id.get(oid) or {}
        if not r:
            continue
        vision = r.get("vision") or {}
        new_attrs = []
        for a in vision.get("new_attributes") or []:
            key = (oid, (a.get("name") or "").casefold(), (a.get("value") or "").casefold())
            if key in keep or any(
                k[0] == oid
                and k[1] == (a.get("name") or "").casefold()
                and (a.get("value") or "").casefold() in k[2]
                for k in keep
            ):
                new_attrs.append(a)
            else:
                # still show if in preferred visual attrs
                n = (a.get("name") or "").casefold()
                if any(x in n for x in ("принт", "силуэт", "капюшон", "вырез", "воротник", "посадка", "застеж")):
                    new_attrs.append(a)
        params = full.get("params") or {}
        feed_keys = [
            k
            for k in params
            if k
            not in {
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
        ]
        feed_snapshot = {k: params[k] for k in feed_keys[:12]}
        # What was NOT in feed
        name = (full.get("name") or r["product"].get("name") or "").casefold()
        feed_blob = (name + " " + " ".join(str(v) for v in feed_snapshot.values())).casefold()
        missing_vs_feed = []
        for a in new_attrs:
            val = (a.get("value") or "").casefold()
            if val and val not in feed_blob:
                missing_vs_feed.append(a)
        cases.append(
            {
                "offer_id": oid,
                "name": full.get("name") or r["product"].get("name"),
                "bucket": full.get("bucket") or r["product"].get("bucket"),
                "category_name": full.get("category_name") or r["product"].get("category_name"),
                "vendor": full.get("vendor") or r["product"].get("vendor"),
                "url": full.get("url") or r["product"].get("url"),
                "picture": r["product"].get("picture") or full.get("picture"),
                "feed_had": feed_snapshot,
                "extracted_new": missing_vs_feed or new_attrs,
                "already_in_feed_visible": vision.get("already_in_feed_visible") or [],
                "partner_one_liner": "",
            }
        )

    # one-liners
    lines = {
        "11302590": "На фото полоска и пуговицы — в фиде только цвет/материал, без принта и застёжки.",
        "13839154": "Вырез-капля и стойка видны на фото; в params нет воротника/выреза.",
        "13661940": "Силуэт «хобо» с фото; в фиде нет типа сумки как атрибута.",
        "13846153": "Капюшон на фото; boolean hood в фиде отсутствует.",
        "13594873": "Клетка тартан на пальто; в name/params типа узора нет.",
    }
    for c in cases:
        c["partner_one_liner"] = lines.get(c["offer_id"], "")

    (OUT / "demo_cases.json").write_text(
        json.dumps({"n": len(cases), "cases": cases}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for c in cases:
        print(c["offer_id"], c["name"][:40], "attrs", len(c["extracted_new"]), c["picture"][:60])


if __name__ == "__main__":
    main()
