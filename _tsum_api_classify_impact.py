# -*- coding: utf-8 -*-
"""
Classify vision-impact TSUM queries via Diginetica API.
API key from partner URL. Single-threaded. size=0 for speed.
Compare with CH isZeroQuery when available.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"
API_URL = "https://sort.diginetica.net/search"
API_KEY = "U08OJ74208"
# Partner URL uses zero_queries_predictor; also try classic zero_queries for parity
STRATEGY = "advanced_xname,zero_queries_predictor"

# Impact query list from refined impact (expanded + direct unique)
IMPACT = OUT / "query_impact_refined.json"
TOP = OUT / "top-30k-queries-ch.json"
STATE = OUT / "api_classify_state.json"
RESULT = OUT / "api_classify_impact.json"


def load_impact_queries() -> list[dict]:
    """Rebuild impact set from same needles as _tsum_impact_refine.TIERS."""
    # Inline copy — avoid import path issues
    families: dict[str, list[str]] = {
        "Принт / узор": [
            "принт", "в клетку", "с полоск", "полосат", "леопард", "цветочн принт",
            "в горошек", "animal print", "с логотипом", "логомания", "монограмм",
            "клетк", "полоск", "цветочн", "горошек", "монограмм", "логотип",
        ],
        "Силуэт / посадка": [
            "оверсайз", "oversize", "slim fit", "wide leg", "клёш", "клеш",
            "приталенн", "а-силуэт", "свободного кроя", "slim", "boyfriend", "skinny",
            "притален",
        ],
        "Капюшон": ["капюшон", "с капюшоном"],
        "Застёжка / детали": [
            "на молнии", "на пуговиц", "со шнуровк", "со стразами", "с вышивк",
            "с бахромой", "пайетк", "плиссе", "стеганая", "стёган", "стразы",
            "кружев", "вышивк", "бахром", "люрекс",
        ],
        "Обувь: каблук / платформа": [
            "на каблуке", "на шпильке", "на платформе", "танкетк", "высокий каблук",
            "низкий каблук", "каблук", "шпилька", "платформ", "лофер", "мюли",
            "слингбек", "челси", "босонож",
        ],
        "Тип сумки": [
            "кроссбоди", "crossbody", "сумка тоут", "тоут сумк", "клатч", "шоппер",
            "сумка багет", "багет ", "хобо", "поясная сумка", "мини сумка",
        ],
        "Парфюм": [
            "туалетная вода", "парфюмерная вода", "eau de parfum", "eau de toilette",
            "ноты ", "с нотами", "туалетная", "цитрус", "ваниль", "древесн",
            "цветочн аромат", "мускус", "уд ",
        ],
        "Воротник / вырез": [
            "воротник стойка", "стойка", "v-образн", "вырез", "хомут", "водолазк",
        ],
    }
    top = {r["q"]: r for r in json.loads(TOP.read_text(encoding="utf-8"))["queries"]}
    seen: set[str] = set()
    rows: list[dict] = []
    for fam, ns in families.items():
        for q, r in top.items():
            if q in seen:
                continue
            if any(n in q for n in ns):
                seen.add(q)
                rows.append(
                    {
                        "q": q,
                        "cnt": int(r["cnt"]),
                        "ch_zero_pct": r.get("zero_pct"),
                        "ch_zero_cnt": r.get("zero_cnt"),
                        "family": fam,
                    }
                )
    rows.sort(key=lambda x: -x["cnt"])
    return rows


def classify(q: str) -> dict | None:
    params = {
        "st": q,
        "apiKey": API_KEY,
        "strategy": STRATEGY,
        "withSku": "false",
        "fullData": "true",
        "withCorrection": "false",
        "withFacets": "false",
        "useCategoryPrediction": "false",
        "size": "0",
        "offset": "0",
        "showUnavailable": "false",
        "useCompletion": "true",
        "preview": "false",
        "sort": "DEFAULT",
        "searchConfiguration": "true",
    }
    try:
        r = requests.get(API_URL, params=params, timeout=20, verify=False)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}", "body": r.text[:200]}
        data = r.json()
        th = int(data.get("totalHits") or 0)
        zq = bool(data.get("zeroQueries"))
        if th == 0:
            kind = "ZERO"
        elif zq:
            kind = "RESERVE"
        else:
            kind = "NORMAL"
        return {
            "totalHits": th,
            "zeroQueries": zq,
            "kind": kind,
            "correction": data.get("correction"),
        }
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    queries = load_impact_queries()
    print(f"impact queries to classify: {len(queries)}")

    done: dict[str, dict] = {}
    if STATE.exists():
        done = json.loads(STATE.read_text(encoding="utf-8"))
        print(f"resume {len(done)}")

    t0 = time.time()
    for i, row in enumerate(queries):
        q = row["q"]
        if q in done and "kind" in done[q]:
            continue
        res = classify(q)
        entry = {**row, **(res or {"error": "null"})}
        done[q] = entry
        if i % 25 == 0:
            elapsed = time.time() - t0
            n = sum(1 for v in done.values() if "kind" in v)
            rps = max(n, 1) / max(elapsed, 0.1)
            print(
                f"  [{n}/{len(queries)}] {rps:.1f} rps  last={q[:40]!r} kind={entry.get('kind')}",
                flush=True,
            )
            STATE.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
        time.sleep(0.05)  # gentle

    STATE.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")

    # Summarize
    kinds = {"ZERO": [], "RESERVE": [], "NORMAL": [], "ERROR": []}
    for q, e in done.items():
        k = e.get("kind") or "ERROR"
        kinds.setdefault(k, []).append(e)

    def sum_cnt(lst):
        return sum(int(x.get("cnt") or 0) for x in lst)

    summary = {
        "strategy": STRATEGY,
        "apiKey_suffix": API_KEY[-4:],
        "n_classified": len(done),
        "by_kind": {
            k: {
                "queries": len(v),
                "searches_90d": sum_cnt(v),
                "top": sorted(v, key=lambda x: -int(x.get("cnt") or 0))[:20],
            }
            for k, v in kinds.items()
            if v
        },
    }

    # CH vs API disagreement: CH zero_pct high but API NORMAL, or CH zero_pct=0 but API RESERVE/ZERO
    disagree = []
    for e in done.values():
        if "kind" not in e:
            continue
        ch_zp = float(e.get("ch_zero_pct") or 0)
        kind = e["kind"]
        # CH marks many searches as zero flag
        ch_mostly_zero = ch_zp >= 50
        api_zeroish = kind in {"ZERO", "RESERVE"}
        if ch_mostly_zero != api_zeroish and (ch_zp >= 20 or api_zeroish):
            disagree.append(
                {
                    "q": e["q"],
                    "cnt": e["cnt"],
                    "ch_zero_pct": ch_zp,
                    "api_kind": kind,
                    "api_hits": e.get("totalHits"),
                }
            )
    disagree.sort(key=lambda x: -x["cnt"])
    summary["ch_vs_api_disagree_top"] = disagree[:40]
    summary["ch_vs_api_disagree_n"] = len(disagree)

    RESULT.write_text(
        json.dumps({"summary": summary, "queries": done}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "top"} for k, v in summary["by_kind"].items()}, ensure_ascii=False, indent=2))
    print("disagree", summary["ch_vs_api_disagree_n"])
    print("Wrote", RESULT)


if __name__ == "__main__":
    main()
