# -*- coding: utf-8 -*-
"""Refined query impact for vision attrs — conservative + expanded, de-duped."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"

# Two tiers for partner honesty
TIERS = {
    "direct_facet": {
        "label": "Прямые facet-запросы (консервативно)",
        "families": {
            "Принт / узор": [
                "принт",
                "в клетку",
                "с полоск",
                "полосат",
                "леопард",
                "цветочн принт",
                "в горошек",
                "animal print",
                "с логотипом",
                "логомания",
                "монограмм",
            ],
            "Силуэт / посадка": [
                "оверсайз",
                "oversize",
                "slim fit",
                "wide leg",
                "клёш",
                "клеш",
                "приталенн",
                "а-силуэт",
                "свободного кроя",
            ],
            "Капюшон": ["капюшон", "с капюшоном"],
            "Застёжка / детали": [
                "на молнии",
                "на пуговиц",
                "со шнуровк",
                "со стразами",
                "с вышивк",
                "с бахромой",
                "пайетк",
                "плиссе",
                "стеганая",
                "стёган",
            ],
            "Обувь: каблук / платформа": [
                "на каблуке",
                "на шпильке",
                "на платформе",
                "танкетк",
                "высокий каблук",
                "низкий каблук",
            ],
            "Тип сумки": [
                "кроссбоди",
                "crossbody",
                "сумка тоут",
                "тоут сумк",
                "клатч",
                "шоппер",
                "сумка багет",
                "багет ",
            ],
            "Парфюм: ноты / концентрация": [
                "туалетная вода",
                "парфюмерная вода",
                "eau de parfum",
                "eau de toilette",
                "ноты ",
                "с нотами",
            ],
            "Воротник / вырез": [
                "воротник стойка",
                "стойка",
                "v-образн",
                "вырез",
                "хомут",
                "водолазк",
            ],
        },
    },
    "expanded_style": {
        "label": "Расширенный стиль (визуальные формулировки + каблук/сумки/принт)",
        "families": {
            "Каблук и обувные формы": [
                "каблук",
                "шпилька",
                "платформ",
                "танкетк",
                "лофер",
                "мюли",
                "слингбек",
                "челси",
                "босонож",
            ],
            "Сумки по силуэту": [
                "кроссбоди",
                "crossbody",
                "клатч",
                "шоппер",
                "багет",
                "хобо",
                "поясная сумка",
                "мини сумка",
            ],
            "Принт и орнамент": [
                "принт",
                "клетк",
                "полоск",
                "леопард",
                "цветочн",
                "горошек",
                "монограмм",
                "логотип",
            ],
            "Посадка и силуэт одежды": [
                "оверсайз",
                "oversize",
                "slim",
                "wide leg",
                "клёш",
                "клеш",
                "boyfriend",
                "skinny",
                "притален",
            ],
            "Декор и фактура": [
                "стразы",
                "пайетк",
                "кружев",
                "вышивк",
                "бахром",
                "стеган",
                "стёган",
                "плиссе",
                "люрекс",
            ],
            "Парфюмерия descriptive": [
                "туалетная",
                "парфюмерная вода",
                "цитрус",
                "ваниль",
                "древесн",
                "цветочн аромат",
                "мускус",
                "уд ",
            ],
        },
    },
}


def main() -> None:
    queries = json.loads((OUT / "top-30k-queries-ch.json").read_text(encoding="utf-8"))["queries"]
    totals_path = OUT / "ch_totals_90d.json"
    totals = json.loads(totals_path.read_text(encoding="utf-8")) if totals_path.exists() else []
    total_all = int(totals[0]["searches"]) if totals else None
    top30k = sum(int(x["cnt"]) for x in queries)

    out = {"top30k_searches": top30k, "ch_totals": totals[0] if totals else None, "tiers": {}}
    for tier_id, tier in TIERS.items():
        fam_stats = {}
        uniq = []
        seen = set()
        for fam, needles in tier["families"].items():
            matched = [r for r in queries if any(n in r["q"] for n in needles)]
            s = sum(int(x["cnt"]) for x in matched)
            fam_stats[fam] = {
                "queries": len(matched),
                "searches_90d": s,
                "examples": [
                    {"q": x["q"], "cnt": int(x["cnt"])}
                    for x in sorted(matched, key=lambda z: -int(z["cnt"]))[:6]
                ],
            }
            for r in matched:
                if r["q"] not in seen:
                    seen.add(r["q"])
                    uniq.append(r)
        searches = sum(int(x["cnt"]) for x in uniq)
        out["tiers"][tier_id] = {
            "label": tier["label"],
            "unique_queries": len(uniq),
            "searches_90d": searches,
            "share_top30k_pct": round(100.0 * searches / max(top30k, 1), 2),
            "share_all_searches_pct": round(100.0 * searches / max(total_all or top30k, 1), 2)
            if total_all
            else None,
            "families": fam_stats,
        }

    (OUT / "query_impact_refined.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for tid, t in out["tiers"].items():
        print(tid, t["unique_queries"], t["searches_90d"], t["share_top30k_pct"])
        for fam, st in sorted(t["families"].items(), key=lambda x: -x[1]["searches_90d"]):
            print(f"  {fam}: {st['searches_90d']} / {st['queries']}q")


if __name__ == "__main__":
    main()
