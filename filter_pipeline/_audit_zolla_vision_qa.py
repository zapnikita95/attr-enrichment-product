#!/usr/bin/env python3
"""Quick QA on Zolla local vision checkpoint."""
from __future__ import annotations

import json
import random
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CKPT = ROOT / "portfolio/zolla_filters/local_catalog/vision_checkpoint.jsonl"
SCHEMA = ROOT / "portfolio/zolla_filters/filter_schema_clean.json"
DB = Path(r"C:\Users\1\OneDrive\Desktop\image_description-main\projects\Zolla\results.db")


def main() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    specs = schema["attributes"]
    allowed = {s["attr_id"]: set(map(str, s["allowed_values"])) for s in specs}
    labels = {s["attr_id"]: s["label_ru"] for s in specs}

    rows = [json.loads(x) for x in CKPT.read_text(encoding="utf-8").splitlines() if x.strip()]
    print(f"n_rows={len(rows)} errors={sum(1 for r in rows if r.get('error'))}")
    print("n_attrs_hist", dict(sorted(Counter(len(r.get("attributes") or []) for r in rows).items())))

    val_c: dict[str, Counter] = defaultdict(Counter)
    oov: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        for a in r.get("attributes") or []:
            if not isinstance(a, dict):
                continue
            aid = str(a.get("attr_id") or "")
            vs = str(a.get("value"))
            if not aid:
                continue
            val_c[aid][vs] += 1
            if aid in allowed and vs not in allowed[aid]:
                oov[aid][vs] += 1

    print("\n=== TOP VALUES / OOV ===")
    for aid in sorted(val_c):
        tot = sum(val_c[aid].values())
        oov_n = sum(oov[aid].values())
        print(f"{labels.get(aid, aid)} ({aid}): n={tot} oov={oov_n}")
        print("  top:", val_c[aid].most_common(10))
        if oov[aid]:
            print("  OOV:", oov[aid].most_common(8))

    # suspicious heuristics
    print("\n=== HEURISTIC RED FLAGS ===")
    flags = Counter()
    examples: dict[str, list] = defaultdict(list)
    con = sqlite3.connect(str(DB))
    for r in rows:
        attrs = {
            a["attr_id"]: a["value"]
            for a in (r.get("attributes") or [])
            if isinstance(a, dict) and a.get("attr_id")
        }
        pk = r.get("picture_key") or ""
        offer = con.execute(
            "SELECT offer_id, name, category FROM results WHERE picture_url=? LIMIT 1",
            (pk,),
        ).fetchone()
        if not offer and "/" in pk:
            offer = con.execute(
                "SELECT offer_id, name, category FROM results WHERE picture_url LIKE ? LIMIT 1",
                ("%" + pk.rsplit("/", 1)[-1],),
            ).fetchone()
        name = (offer[1] or "").lower() if offer else ""
        cat = (offer[2] or "").lower() if offer else ""

        # length on clearly non-dress-like short names? soft
        if attrs.get("quilted") == "да" and "стег" not in name and "пуховик" not in name:
            # not necessarily wrong
            pass
        if attrs.get("hood") == "да" and any(x in name for x in ("юбк", "брюк", "джинс", "шорт")):
            flags["hood_on_bottoms_title"] += 1
            if len(examples["hood_on_bottoms_title"]) < 5:
                examples["hood_on_bottoms_title"].append((offer, attrs))
        if attrs.get("collar") == "отложной" and attrs.get("hood") == "да":
            flags["collar_with_hood"] += 1
            if len(examples["collar_with_hood"]) < 5:
                examples["collar_with_hood"].append((offer, attrs))
        if attrs.get("length") in {"mini", "midi", "maxi"} and any(
            x in cat for x in ("аксессуар", "обувь", "бельё", "белье", "носк")
        ):
            flags["length_on_weird_cat"] += 1
            if len(examples["length_on_weird_cat"]) < 5:
                examples["length_on_weird_cat"].append((offer, attrs))
        if attrs.get("print_pattern") == "однотонный" and any(
            x in name for x in ("полоск", "клетк", "горош", "цвет", "принт", "леопард")
        ):
            flags["solid_vs_print_in_title"] += 1
            if len(examples["solid_vs_print_in_title"]) < 8:
                examples["solid_vs_print_in_title"].append((offer, attrs))
        if attrs.get("sleeve_length") == "без рукавов" and "рукав" in name and "без" not in name:
            flags["sleeveless_vs_sleeve_title"] += 1
            if len(examples["sleeveless_vs_sleeve_title"]) < 5:
                examples["sleeveless_vs_sleeve_title"].append((offer, attrs))
        if attrs.get("fastener") == "молния" and "пуговиц" in name:
            flags["zip_vs_buttons_title"] += 1
            if len(examples["zip_vs_buttons_title"]) < 5:
                examples["zip_vs_buttons_title"].append((offer, attrs))

    for k, n in flags.most_common():
        print(f"{k}: {n}")
        for offer, attrs in examples[k]:
            print(f"  {offer[0] if offer else '?'} | {(offer[1] or '')[:70] if offer else '?'}")
            print(f"    {attrs}")

    # random visual-ish spot: title vs attrs
    print("\n=== RANDOM SPOT (title vs vision) ===")
    random.seed(42)
    for r in random.sample(rows, min(20, len(rows))):
        pk = r.get("picture_key") or ""
        offer = con.execute(
            "SELECT offer_id, name, category FROM results WHERE picture_url=? LIMIT 1",
            (pk,),
        ).fetchone()
        attrs = {
            a["attr_id"]: a["value"]
            for a in (r.get("attributes") or [])
            if isinstance(a, dict) and a.get("attr_id")
        }
        print(f"- {offer[0] if offer else '?'} | {(offer[1] or '?')[:75]}")
        print(f"  cat={(offer[2] or '')[:55] if offer else '?'}")
        print(f"  {attrs}")
    # title vs vision heuristics (may include feed picture bugs)
    mismatch = 0
    okish = 0
    accessory_pollute = 0
    acc_kw = ("сумк", "перчат", "шапк", "шарф", "ремн", "носк", "трус", "купальн", "плавк")
    bottom_kw = ("брюк", "джинс", "юбк", "шорт")
    for r in rows:
        pk = r.get("picture_key") or ""
        offer = con.execute(
            "SELECT name FROM results WHERE picture_url=? LIMIT 1", (pk,)
        ).fetchone()
        if not offer:
            continue
        name = (offer[0] or "").lower()
        attrs = {
            a["attr_id"]: a["value"]
            for a in (r.get("attributes") or [])
            if isinstance(a, dict) and a.get("attr_id")
        }
        if any(k in name for k in acc_kw):
            if attrs.get("hood") == "да" or attrs.get("sleeve_length") in {
                "длинный",
                "короткий",
                "3/4",
            }:
                accessory_pollute += 1
        bad = False
        if any(k in name for k in bottom_kw) and attrs.get("hood") == "да":
            bad = True
        if "длинн" in name and "рукав" in name and attrs.get("sleeve_length") == "без рукавов":
            bad = True
        if "клетк" in name and attrs.get("print_pattern") == "однотонный":
            bad = True
        if bad:
            mismatch += 1
        else:
            okish += 1
    print(
        f"\n=== TITLE vs VISION === mismatch≈{mismatch} okish≈{okish} "
        f"accessory_pollute≈{accessory_pollute} / {len(rows)}"
    )
    con.close()


if __name__ == "__main__":
    main()
