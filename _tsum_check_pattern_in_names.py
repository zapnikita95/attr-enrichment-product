# -*- coding: utf-8 -*-
"""Check whether pattern/print lexicon appears in offer names vs params."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from xml.etree.ElementTree import iterparse

FEED = Path(r"C:\Users\1\Downloads\tsum.xml")
OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"

NEEDLES = [
    "принт",
    "клетк",
    "полоск",
    "полосат",
    "леопард",
    "горошек",
    "цветочн",
    "монограмм",
    "логотип",
    "логомани",
    "animal",
    "check",
    "stripe",
    "striped",
    "floral",
    "paisley",
    "зебр",
    "абстракт",
    "орнамент",
    "узор",
]


def local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def main() -> None:
    offers = 0
    in_name = Counter()
    in_params = Counter()
    in_details = Counter()
    in_custom = Counter()
    name_only = Counter()  # needle in name but NOT in any param text
    examples: dict[str, list[dict]] = {n: [] for n in NEEDLES}
    any_in_name = 0
    any_in_params = 0
    any_in_either = 0
    any_in_name_not_params = 0

    for _ev, elem in iterparse(str(FEED), events=("end",)):
        if local(elem.tag) != "offer":
            continue
        offers += 1
        name = ""
        params: dict[str, str] = {}
        for child in elem:
            ct = local(child.tag)
            if ct == "name":
                name = (child.text or "").strip()
            elif ct == "param":
                pn = (child.get("name") or "").strip()
                params[pn] = (child.text or "").strip()
        name_l = name.casefold().replace("ё", "е")
        params_blob = " ".join(params.values()).casefold().replace("ё", "е")
        details = (params.get("attribute_details") or "").casefold().replace("ё", "е")
        custom = (params.get("custom categories") or "").casefold().replace("ё", "е")

        hn_any = False
        hp_any = False
        for n in NEEDLES:
            hit_name = n in name_l
            hit_params = n in params_blob
            hit_det = n in details
            hit_cust = n in custom
            if hit_name:
                in_name[n] += 1
                hn_any = True
            if hit_params:
                in_params[n] += 1
                hp_any = True
            if hit_det:
                in_details[n] += 1
            if hit_cust:
                in_custom[n] += 1
            if hit_name and not hit_params:
                name_only[n] += 1
            if (hit_name or hit_params) and len(examples[n]) < 5:
                examples[n].append(
                    {
                        "name": name[:120],
                        "in_name": hit_name,
                        "in_params": hit_params,
                        "details": params.get("attribute_details", "")[:80],
                        "custom": (params.get("custom categories") or "")[:80],
                    }
                )
        if hn_any:
            any_in_name += 1
        if hp_any:
            any_in_params += 1
        if hn_any or hp_any:
            any_in_either += 1
        if hn_any and not hp_any:
            any_in_name_not_params += 1
        elem.clear()
        if offers % 100000 == 0:
            print(f"... {offers}")

    report = {
        "offers_total": offers,
        "needles": NEEDLES,
        "per_needle": {
            n: {
                "in_name": in_name[n],
                "in_params": in_params[n],
                "in_attribute_details": in_details[n],
                "in_custom_categories": in_custom[n],
                "name_only_not_in_params": name_only[n],
                "name_pct": round(100.0 * in_name[n] / max(offers, 1), 3),
                "params_pct": round(100.0 * in_params[n] / max(offers, 1), 3),
                "examples": examples[n],
            }
            for n in NEEDLES
        },
        "union_any_needle": {
            "in_name": any_in_name,
            "in_params": any_in_params,
            "in_either": any_in_either,
            "name_only_not_in_params": any_in_name_not_params,
            "name_pct": round(100.0 * any_in_name / max(offers, 1), 3),
            "params_pct": round(100.0 * any_in_params / max(offers, 1), 3),
            "either_pct": round(100.0 * any_in_either / max(offers, 1), 3),
        },
    }
    (OUT / "pattern_name_coverage.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report["union_any_needle"], ensure_ascii=False, indent=2))
    print("\nTop needles by name hits:")
    for n, c in in_name.most_common(15):
        print(
            f"  {n:12} name={c:6} params={in_params[n]:6} details={in_details[n]:5} "
            f"name_only={name_only[n]:5}"
        )


if __name__ == "__main__":
    main()
