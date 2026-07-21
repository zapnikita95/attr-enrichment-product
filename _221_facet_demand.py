# -*- coding: utf-8 -*-
"""Facet demand proofs for 221 vision KEEP attrs (TSUM-style) + Metrika status."""
from __future__ import annotations

import csv
import json
import re
import urllib3
from collections import Counter
from pathlib import Path

import requests

urllib3.disable_warnings()

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "portfolio" / "221_azbuka"
DESK = Path(r"C:\Users\1\OneDrive\Desktop")
CSV = DESK / "221_azbuka_vision_dashboard_upload.csv"

CH_URL = "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443"
CH_AUTH = ("digi-admin", "Fl2bSowt")
SITE_ID = 221

# From text-impact study
AOV = 6192.55
UPLIFT_STRONG = 0.0233 * 0.5  # half of (exact−fallback)
UPLIFT_FLAVOR = 0.008 * 0.25  # phrase share 25%

# Curated facet families — direct packshot language (как §4 у ЦУМ)
FACET_FAMILIES: list[dict] = [
    {
        "attr": "Форма выпуска",
        "tier": "strong",
        "why": "Форма фасовки с упаковки: мельница, пауч, зёрна, хлопья — редко в name",
        "impact": "Поднимает точность выдачи по форме (мельница/пауч/зёрна) → меньше fallback",
        "patterns": [
            r"\bмельниц",
            r"\bпауч",
            r"\bpouch\b",
            r"\bдойпак",
            r"\bdoypack\b",
            r"\bв зерн",
            r"\bзерн[аые]\b",
            r"\bмолот(ый|ое|ые)?\b",
            r"\bхлопь",
            r"\bгранул",
            r"\bпюре\b",
            r"\bснек",
            r"\bподарочн(ый|ые)?\s+набор",
            r"\bнабор\s+подароч",
        ],
    },
    {
        "attr": "Тип упаковки",
        "tier": "strong",
        "why": "Тип тары как фильтр: дойпак, стекло, банка, саше",
        "impact": "Фильтр/матч по таре — пользователь ищет «в стекле», «дойпак»",
        "patterns": [
            r"\bдойпак",
            r"\bdoypack\b",
            r"\bстекл(о|янн)",
            r"\bв банке\b",
            r"\bсаше\b",
            r"\bтуба\b",
            r"\bдой-?пак",
        ],
    },
    {
        "attr": "Вкус, Добавки",
        "tier": "flavor",
        "why": "Вкус/label с этикетки, которого нет в названии (brownie, чили…)",
        "impact": "Label-вкус цепляет long-tail («чипсы brownie», «с трюфелем»)",
        "patterns": [
            r"\bbrownie\b",
            r"\bбрауни\b",
            r"\bчили\b",
            r"\bбарбекю\b",
            r"\bbarbeque\b",
            r"\bwasabi\b",
            r"\bвасаби\b",
            r"\bтрюфел",
            r"\bпармезан",
            r"\bс перцем\b",
            r"\bс чесноком\b",
            r"\bс луком\b",
            r"\bс грибами\b",
            r"\bс беконом\b",
            r"\bкарамел",
            r"\bмед(ов|овый|овое)",
            r"\bпаприк",
            r"\bбекон",
            r"\bхалапень",
            r"\bjalapeno\b",
        ],
    },
    {
        "attr": "Технология приготовления",
        "tier": "strong",
        "why": "Hand cooked / kettle с этикетки",
        "impact": "Премиум-сигнал на чипсах/снеках — прямой facet",
        "patterns": [
            r"\bhand\s*cooked\b",
            r"\bhandcooked\b",
            r"\bkettle\b",
            r"\bручн(ая|ой)\s*жар",
        ],
    },
    {
        "attr": "Способ обработки",
        "tier": "strong",
        "why": "Позитивный OCR: засахаренные, вяленые, сушёные",
        "impact": "Запрос «вяленые / засахаренные» → SKU с OCR-атрибутом",
        "patterns": [
            r"\bзасахар",
            r"\bвялен",
            r"\bсушен",
            r"\bсушён",
            r"\bcandied\b",
        ],
    },
    {
        "attr": "Нарезка",
        "tier": "strong",
        "why": "Ломтики / кусочки / слайсы",
        "impact": "Уточнение формы нарезки в выдаче",
        "patterns": [
            r"\bломтик",
            r"\bкусочк",
            r"\bслайс",
            r"\bslices?\b",
            r"\bchunks?\b",
            r"\bнарезк",
            r"\bпластин",
        ],
    },
    {
        "attr": "Тип соуса",
        "tier": "strong",
        "why": "Pet: в соусе / в желе с пауча",
        "impact": "Узкий pet-facet, но прямой матч",
        "patterns": [
            r"\bкорм.+\bв соусе\b",
            r"\bкорм.+\bв желе\b",
            r"\bв соусе\b.+\b(кош|кот|собак|щен)",
            r"\bв желе\b.+\b(кош|кот|собак|щен)",
            r"\bin gravy\b",
            r"\bin jelly\b",
            r"\bfelix.+\bжеле",
            r"\bsheba.+\bжеле",
            r"\bwhiskas.+\bжеле",
        ],
    },
    {
        "attr": "Текстура корма",
        "tier": "strong",
        "why": "Pet: филе / паштет / мусс с этикетки",
        "impact": "Текстура корма как facet",
        "patterns": [
            r"\bкорм.+\bпаштет",
            r"\bпаштет.+\b(кош|кот|собак|щен|корм)",
            r"\bкорм.+\bмусс",
            r"\bмусс.+\b(кош|кот|корм)",
            r"\bкорм.+\bфиле",
            r"\bsheba.+\bпаштет",
            r"\bgourmet.+\bпаштет",
            r"\bfelix.+\bпаштет",
        ],
    },
]


def normalize(s: str) -> str:
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"[^a-zа-я0-9\s]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def ch_query(sql: str, timeout: int = 180) -> list[dict]:
    r = requests.post(
        CH_URL,
        auth=CH_AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=timeout,
        verify=False,
    )
    if r.status_code != 200:
        print("CH ERR", r.status_code, r.text[:400])
        return []
    return r.json().get("data") or []


def fetch_top_queries(limit: int = 50000) -> list[tuple[str, int]]:
    rows = ch_query(
        f"""
SELECT lowerUTF8(searchTerm) AS q, count() AS c
FROM sessions.searches
WHERE siteId = {SITE_ID}
  AND toDate(timestamp) >= today() - 90
  AND toDate(timestamp) <= today() - 1
  AND searchTerm != ''
GROUP BY q
ORDER BY c DESC
LIMIT {limit}
"""
    )
    out = []
    for r in rows:
        q = normalize(str(r.get("q") or ""))
        c = int(float(r.get("c") or 0))
        if q and c > 0:
            out.append((q, c))
    return out


def fetch_baseline() -> dict:
    sess = ch_query(
        f"""
SELECT
  count() AS sessions,
  countIf(searches > 0 OR autocompleteClicks > 0) AS with_search,
  sum(withOrder) AS orders,
  round(sumIf(revenue, withOrder > 0), 2) AS revenue
FROM sessions.agg_sessions
WHERE siteId = {SITE_ID}
  AND toDate(timeBegin) >= today() - 90
  AND toDate(timeBegin) <= today() - 1
"""
    )
    searches = ch_query(
        f"""
SELECT count() AS searches
FROM sessions.searches
WHERE siteId = {SITE_ID}
  AND toDate(timestamp) >= today() - 90
  AND toDate(timestamp) <= today() - 1
"""
    )
    base = sess[0] if sess else {}
    base["searches_90d"] = int(float((searches[0] if searches else {}).get("searches") or 0))
    return base


def load_keep_counts() -> dict[str, int]:
    c: Counter[str] = Counter()
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            c[(r.get("attribute_name") or "").strip()] += 1
    return dict(c)


def match_family(q: str, patterns: list[str]) -> bool:
    return any(re.search(p, q, re.I) for p in patterns)


def main() -> None:
    print("fetching CH queries…")
    queries = fetch_top_queries(50000)
    total_s = sum(s for _, s in queries)
    print(f"queries={len(queries)} volume_top={total_s}")
    baseline = fetch_baseline()
    print("baseline", baseline)

    keep = load_keep_counts()
    families = []
    for fam in FACET_FAMILIES:
        pats = fam["patterns"]
        hits = [(q, s) for q, s in queries if match_family(q, pats)]
        vol = sum(s for _, s in hits)
        uniq = len(hits)
        top = hits[:10]
        uplift = UPLIFT_STRONG if fam["tier"] == "strong" else UPLIFT_FLAVOR
        rev_90 = vol * uplift * AOV
        families.append(
            {
                "attr": fam["attr"],
                "tier": fam["tier"],
                "why": fam["why"],
                "impact": fam["impact"],
                "keep_rows": keep.get(fam["attr"], 0),
                "searches_90d": vol,
                "unique_queries": uniq,
                "uplift_pp": round(uplift * 100, 3),
                "delta_rub_90d": round(rev_90, 0),
                "delta_rub_month": round(rev_90 / 3, 0),
                "top_queries": [{"q": q, "s": s} for q, s in top],
                "examples": ", ".join(q for q, _ in top[:3]) if top else "—",
            }
        )
        print(
            f"  {fam['attr']}: {vol} searches / {uniq} q ~ "
            f"{rev_90/3:,.0f} RUB/mo | {top[:3]}"
        )

    total_month = sum(f["delta_rub_month"] for f in families)
    out = {
        "site_id": SITE_ID,
        "period": "90d",
        "source_queries": "ClickHouse sessions.searches siteId=221",
        "metrika": {
            "available": False,
            "counter_id": None,
            "note": (
                "В реестре Diginetica top50 для av.ru: has_metrika=false, counter_id=null. "
                "OAuth Метрики Digi (409 счётчиков) — совпадений av.ru / Азбука нет. "
                "Поэтому базу ecommerce и CVR берём из Diginetica CH + partner study "
                "(как для остальных no-metrika партнёров). "
                "Чтобы перейти на Метрику как у ЦУМ — нужен доступ партнёра к счётчику."
            ),
        },
        "aov": AOV,
        "query_universe": {"unique_q_top50k": len(queries), "volume_top50k": total_s},
        "baseline_ch": baseline,
        "facet_families": families,
        "stream_a_month_sum": total_month,
    }
    path = OUT / "vision_facet_demand.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", path, "stream_a_month", total_month)


if __name__ == "__main__":
    main()
