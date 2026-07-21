# -*- coding: utf-8 -*-
"""Gap: search query tokens vs feed name/params; needle families for vision attrs."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree.ElementTree import iterparse

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"
FEED = Path(r"C:\Users\1\Downloads\tsum.xml")
QUERIES = OUT / "top-30k-queries-ch.json"

# Visual / OCR attribute families relevant for fashion luxury + beauty
NEEDLE_FAMILIES: dict[str, list[str]] = {
    "pattern_print": [
        "принт",
        "клетка",
        "полоск",
        "леопард",
        "зебр",
        "цветочн",
        "горошек",
        "абстракт",
        "логотип",
        "monogram",
        "пейсли",
        "змеин",
        "animal print",
        "check",
        "stripe",
        "floral",
    ],
    "silhouette_fit": [
        "оверсайз",
        "oversize",
        "slim",
        "straight",
        "wide leg",
        "клёш",
        "клеш",
        "bootcut",
        "boyfriend",
        "mom",
        "skinny",
        "а-силуэт",
        "трапец",
        "притален",
        "свободн кро",
    ],
    "neckline_sleeve_hood": [
        "капюшон",
        "hood",
        "стойка",
        "воротник",
        "v-образ",
        "вырез",
        "водолаз",
        "хомут",
        "без рукав",
        "короткий рукав",
        "длинный рукав",
        "3/4",
        "открытые плечи",
        "бретел",
    ],
    "length": ["мини", "миди", "макси", "до колена", "укорочен", "длинн плать", "коротк плат"],
    "material_visible": [
        "кашемир",
        "шёлк",
        "шелк",
        "лён",
        "лен",
        "замш",
        "кожа",
        "мех",
        "твид",
        "деним",
        "джинс",
        "хлопок",
        "шерсть",
        "атлас",
        "кружев",
        "пайетк",
        "люрекс",
    ],
    "shoe_details": [
        "каблук",
        "шпилька",
        "платформ",
        "танкетк",
        "шнурк",
        "лофер",
        "мюли",
        "слингбек",
        "босонож",
        "челси",
        "массивн",
        "тракторн",
    ],
    "bag_type": [
        "кроссбоди",
        "crossbody",
        "тоут",
        "tote",
        "клатч",
        "рюкзак",
        "шоппер",
        "багет",
        "седло",
        "поясн сум",
        "мини сум",
    ],
    "decor_hardware": [
        "стразы",
        "жемчуг",
        "бахрам",
        "заклепк",
        "цеп",
        "пряжк",
        "вышивк",
        "аппликац",
        "пуговиц",
        "молни",
    ],
    "perfume_notes": [
        "парфюм",
        "туалетная вода",
        "eau de",
        "edp",
        "edt",
        "цитрус",
        "ваниль",
        "уд ",
        " oud",
        "древесн",
        "цветочн",
        "мускус",
        "амбр",
        "бергамот",
        "жасмин",
        "роза ",
        "сандал",
    ],
    "color_nuance": [
        "бордо",
        "изумруд",
        "горчичн",
        "пудров",
        "молочн",
        "кремов",
        "терракот",
        "оливков",
        "лаванд",
        "фуксия",
        "металлик",
        "золотист",
        "серебрист",
    ],
}

STOP = {
    "для",
    "и",
    "или",
    "на",
    "с",
    "без",
    "из",
    "в",
    "по",
    "the",
    "and",
    "of",
    "a",
    "женская",
    "женский",
    "мужская",
    "мужской",
    "детская",
    "детский",
}


def local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def tokenize(text: str) -> set[str]:
    text = (text or "").lower().replace("ё", "е")
    toks = re.findall(r"[a-zа-я0-9&]+", text, flags=re.I)
    return {t for t in toks if len(t) >= 3 and t not in STOP}


def build_feed_stem_sample(max_offers: int = 80000) -> tuple[set[str], Counter]:
    """Sample feed indexed text (name+params, no ids) for coverage estimate."""
    corpus_tokens: Counter = Counter()
    n = 0
    skip_params = {
        "brand_id",
        "model_id",
        "product_id",
        "color_concrete_id",
        "color_base_id",
        "size_id",
        "date_create",
        "лого",
        "штрихкод",
        "артикул",
    }
    for event, elem in iterparse(str(FEED), events=("end",)):
        if local(elem.tag) != "offer":
            continue
        n += 1
        parts = []
        for child in elem:
            ct = local(child.tag)
            if ct == "name":
                parts.append(child.text or "")
            elif ct == "vendor":
                parts.append(child.text or "")
            elif ct == "param":
                pn = (child.get("name") or "").strip()
                if pn.lower() in skip_params:
                    continue
                parts.append(f"{pn} {child.text or ''}")
        for t in tokenize(" ".join(parts)):
            corpus_tokens[t] += 1
        elem.clear()
        if n >= max_offers:
            break
    return set(corpus_tokens), corpus_tokens


def main() -> None:
    qdata = json.loads(QUERIES.read_text(encoding="utf-8"))
    queries = qdata["queries"]

    # Needle family impact
    family_hits: dict[str, dict] = {}
    for fam, needles in NEEDLE_FAMILIES.items():
        matched = []
        seen = set()
        for r in queries:
            q = r["q"]
            if any(n in q for n in needles):
                if q in seen:
                    continue
                seen.add(q)
                matched.append(r)
        searches = sum(int(x["cnt"]) for x in matched)
        family_hits[fam] = {
            "unique_queries": len(matched),
            "searches_90d": searches,
            "examples": [
                {"q": x["q"], "cnt": int(x["cnt"]), "zero_pct": x["zero_pct"]}
                for x in sorted(matched, key=lambda z: -int(z["cnt"]))[:12]
            ],
        }

    print("Building feed token sample...")
    feed_set, feed_counts = build_feed_stem_sample(80000)
    print(f"feed tokens (sample 80k offers): {len(feed_set)}")

    # Per-query residual: tokens in query not in feed sample
    residual_queries = []
    covered_fully = 0
    gap_searches = 0
    covered_searches = 0
    residual_token_freq = Counter()

    for r in queries:
        q = r["q"]
        cnt = int(r["cnt"])
        toks = tokenize(q)
        if not toks:
            continue
        missing = sorted(t for t in toks if t not in feed_set)
        if not missing:
            covered_fully += 1
            covered_searches += cnt
        else:
            gap_searches += cnt
            for t in missing:
                residual_token_freq[t] += cnt
            residual_queries.append(
                {
                    "q": q,
                    "cnt": cnt,
                    "zero_pct": r["zero_pct"],
                    "missing_tokens": missing,
                    "tokens": sorted(toks),
                }
            )

    # Classify residual tokens into vision-likely vs brand/model noise
    brandish = re.compile(
        r"^[a-z]{2,}$|gucci|dior|chanel|prada|lv|louis|vuitton|hermes|ysl|valentino|balenciaga|versace|fendi|celine|loewe|bottega|moncler|canada|premiata|diesel|zimmermann|brunello|cucinelli",
        re.I,
    )
    vision_residual = []
    for tok, freq in residual_token_freq.most_common(500):
        # skip pure brands / short latin only if looks like brand query residue
        vision_residual.append({"token": tok, "freq_sum": freq, "in_feed_sample": tok in feed_set})

    # Map residual tokens to families
    fam_residual_searches = {}
    for fam, needles in NEEDLE_FAMILIES.items():
        # queries already matched by needle that still have residual OR needle token missing from feed
        s = 0
        for r in residual_queries:
            q = r["q"]
            if any(n in q for n in needles):
                s += r["cnt"]
        fam_residual_searches[fam] = s

    # Vision-addressable estimate: sum of family needle searches (unique queries de-duped)
    vision_q = set()
    vision_searches = 0
    for fam, info in family_hits.items():
        for ex in info["examples"]:
            pass
        # recount unique across all families
    all_vision = []
    seen_q = set()
    for fam, needles in NEEDLE_FAMILIES.items():
        for r in queries:
            q = r["q"]
            if q in seen_q:
                continue
            if any(n in q for n in needles):
                seen_q.add(q)
                all_vision.append(r)
    vision_searches = sum(int(x["cnt"]) for x in all_vision)

    # Among vision-family queries, how many still have residual tokens (true gap)
    vision_gap = [r for r in residual_queries if r["q"] in seen_q]
    vision_gap_searches = sum(r["cnt"] for r in vision_gap)

    report = {
        "site_id": 203,
        "partner": "TSUM",
        "period_days": 90,
        "queries_analyzed": len(queries),
        "total_searches_in_top30k": sum(int(x["cnt"]) for x in queries),
        "feed_sample_offers": 80000,
        "feed_unique_tokens_sample": len(feed_set),
        "queries_fully_covered_by_feed_sample": covered_fully,
        "queries_with_residual_tokens": len(residual_queries),
        "searches_fully_covered": covered_searches,
        "searches_with_residual": gap_searches,
        "residual_rate_searches_pct": round(
            100.0 * gap_searches / max(covered_searches + gap_searches, 1), 2
        ),
        "top_residual_tokens": residual_token_freq.most_common(80),
        "needle_families": family_hits,
        "needle_families_residual_searches": fam_residual_searches,
        "vision_family_unique_queries": len(all_vision),
        "vision_family_searches_90d": vision_searches,
        "vision_family_gap_queries": len(vision_gap),
        "vision_family_gap_searches_90d": vision_gap_searches,
        "top_vision_gap_queries": sorted(vision_gap, key=lambda x: -x["cnt"])[:80],
        "top_residual_queries_overall": sorted(residual_queries, key=lambda x: -x["cnt"])[:80],
    }
    (OUT / "gap_analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: report[k] for k in report if k not in {
        "needle_families", "top_residual_tokens", "top_vision_gap_queries", "top_residual_queries_overall",
        "needle_families_residual_searches"
    }}, ensure_ascii=False, indent=2))
    print("\nFamily searches:")
    for fam, info in sorted(family_hits.items(), key=lambda x: -x[1]["searches_90d"]):
        print(f"  {fam:25} q={info['unique_queries']:4} searches={info['searches_90d']:8} residual≈{fam_residual_searches[fam]}")
    print("Wrote", OUT / "gap_analysis.json")


if __name__ == "__main__":
    main()
