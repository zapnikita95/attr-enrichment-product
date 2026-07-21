# -*- coding: utf-8 -*-
"""
TSUM money impact from vision attrs — partner numbers in RUB.

Uses Diginetica API kinds (source of truth for RESERVE/ZERO/NORMAL).
CVR/AOV from ClickHouse site 203, 90d.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"
API = "https://sort.diginetica.net/search"
KEY = "U08OJ74208"


def api_kind(q: str, strategy: str) -> dict:
    r = requests.get(
        API,
        params={
            "st": q,
            "apiKey": KEY,
            "strategy": strategy,
            "size": 0,
            "fullData": "true",
            "withSku": "false",
            "preview": "false",
        },
        timeout=20,
        verify=False,
    )
    d = r.json()
    th = int(d.get("totalHits") or 0)
    zq = bool(d.get("zeroQueries"))
    kind = "ZERO" if th == 0 else ("RESERVE" if zq else "NORMAL")
    return {"totalHits": th, "zeroQueries": zq, "kind": kind}


def main() -> None:
    metrics = json.loads((OUT / "ch_money_metrics.json").read_text(encoding="utf-8"))
    api = json.loads((OUT / "api_classify_impact.json").read_text(encoding="utf-8"))
    overall = metrics["overall"]
    by_flag = {b["bucket"]: b for b in metrics["by_session_zero_flag"]}

    # CVR baselines from CH
    cvr_normal_flag = float(by_flag["only_normal_flag"]["cvr_pct"]) / 100.0  # 0.00083
    cvr_zero = 0.0
    # Measured on API-classified impact queries (top80 terms each):
    # RESERVE sessions → 0 orders; NORMAL → ~0.066%
    measured_path = OUT / "ch_cvr_by_api_kind.json"
    if measured_path.exists():
        measured = json.loads(measured_path.read_text(encoding="utf-8"))
        cvr_reserve = float(measured.get("reserve", {}).get("cvr_pct") or 0) / 100.0
        cvr_normal_impact = float(measured.get("normal", {}).get("cvr_pct") or 0) / 100.0
    else:
        cvr_reserve = 0.0
        cvr_normal_impact = cvr_normal_flag
    # Target "точный" = max(normal flag, measured normal impact)
    cvr_normal = max(cvr_normal_flag, cvr_normal_impact)
    aov_search = float(overall["avg_check_search_rub"])  # ~100276
    aov_site = 110403.17  # from sitewide sanity
    search_rev_90d = float(overall["search_revenue_90d"])

    # Strategy compare on disagree sample
    disagree = api["summary"].get("ch_vs_api_disagree_top") or []
    strat_cmp = []
    for row in disagree[:12]:
        q = row["q"]
        a = api_kind(q, "advanced_xname,zero_queries_predictor")
        b = api_kind(q, "advanced_xname,zero_queries")
        strat_cmp.append({"q": q, "cnt": row["cnt"], "predictor": a, "classic": b, "ch_zero_pct": row["ch_zero_pct"]})

    kinds = api["summary"]["by_kind"]
    reserve_searches = int(kinds.get("RESERVE", {}).get("searches_90d") or 0)
    normal_searches = int(kinds.get("NORMAL", {}).get("searches_90d") or 0)
    zero_searches = int(kinds.get("ZERO", {}).get("searches_90d") or 0)
    reserve_q = int(kinds.get("RESERVE", {}).get("queries") or 0)
    normal_q = int(kinds.get("NORMAL", {}).get("queries") or 0)
    zero_q = int(kinds.get("ZERO", {}).get("queries") or 0)

    # Scenarios
    scenarios = {
        "conservative": {
            "label": "Консервативный",
            "aov": aov_search,
            "reserve_fixable": 0.70,
            "zero_fixable": 0.40,
            "normal_fixable": 0.25,
            "normal_relative_lift": 0.15,  # +15% к CVR точных
            "reserve_new_cvr": cvr_normal,  # → точный
            "zero_new_cvr": cvr_normal * 0.5,  # половина нормы (новые в выдаче)
        },
        "base": {
            "label": "Базовый (рекомендуем партнёру)",
            "aov": aov_search,
            "reserve_fixable": 0.80,
            "zero_fixable": 0.50,
            "normal_fixable": 0.35,
            "normal_relative_lift": 0.20,
            "reserve_new_cvr": cvr_normal,
            "zero_new_cvr": cvr_normal * 0.5,
        },
        "optimistic": {
            "label": "Оптимистичный",
            "aov": aov_site,
            "reserve_fixable": 0.90,
            "zero_fixable": 0.60,
            "normal_fixable": 0.45,
            "normal_relative_lift": 0.25,
            "reserve_new_cvr": cvr_normal,
            "zero_new_cvr": cvr_normal,
        },
    }

    def calc(sc: dict) -> dict:
        aov = sc["aov"]
        # RESERVE → exact
        d_reserve = sc["reserve_new_cvr"] - cvr_reserve
        rev_reserve_90 = reserve_searches * sc["reserve_fixable"] * d_reserve * aov
        # ZERO → (half/full) normal
        d_zero = sc["zero_new_cvr"] - cvr_zero
        rev_zero_90 = zero_searches * sc["zero_fixable"] * d_zero * aov
        # NORMAL → more precise
        cvr_new_n = cvr_normal * (1.0 + sc["normal_relative_lift"])
        d_normal = cvr_new_n - cvr_normal
        rev_normal_90 = normal_searches * sc["normal_fixable"] * d_normal * aov
        total_90 = rev_reserve_90 + rev_zero_90 + rev_normal_90
        return {
            "reserve_delta_cvr_pp": round(d_reserve * 100, 4),
            "zero_delta_cvr_pp": round(d_zero * 100, 4),
            "normal_delta_cvr_pp": round(d_normal * 100, 4),
            "revenue_90d": {
                "reserve_to_exact": round(rev_reserve_90),
                "zero_to_found": round(rev_zero_90),
                "normal_precision": round(rev_normal_90),
                "total": round(total_90),
            },
            "revenue_month": {
                "reserve_to_exact": round(rev_reserve_90 / 3),
                "zero_to_found": round(rev_zero_90 / 3),
                "normal_precision": round(rev_normal_90 / 3),
                "total": round(total_90 / 3),
            },
            "revenue_year": {"total": round(total_90 / 3 * 12)},
        }

    results = {k: {**v, "calc": calc(v)} for k, v in scenarios.items()}

    # Top reserve examples for partner table
    reserve_top = kinds.get("RESERVE", {}).get("top") or []
    # Per-query money for top reserve (base scenario)
    sc = scenarios["base"]
    d_r = sc["reserve_new_cvr"] - cvr_reserve
    top_rows = []
    for e in reserve_top[:30]:
        cnt = int(e.get("cnt") or 0)
        delta_mo = cnt / 3 * sc["reserve_fixable"] * d_r * sc["aov"]
        top_rows.append(
            {
                "q": e.get("q"),
                "searches_90d": cnt,
                "searches_mo": round(cnt / 3, 1),
                "api_hits": e.get("totalHits"),
                "family": e.get("family"),
                "delta_rub_mo": round(delta_mo),
            }
        )

    report = {
        "partner": "TSUM",
        "site_id": 203,
        "period_days": 90,
        "api": {
            "key_suffix": KEY[-4:],
            "strategy": "advanced_xname,zero_queries_predictor",
            "note": "CH isZeroQuery ≠ API RESERVE: на impact-запросах API дал 0 ZERO, 356 RESERVE. CH zero-flag часто спорит с API (см. strategy_compare).",
        },
        "baselines_ch": {
            "search_sessions_90d": overall["search_sessions"],
            "search_session_cvr_pct": overall["search_session_cvr_pct"],
            "normal_session_cvr_pct": round(cvr_normal * 100, 4),
            "normal_flag_cvr_pct": round(cvr_normal_flag * 100, 4),
            "normal_impact_top80_cvr_pct": round(cvr_normal_impact * 100, 4),
            "zero_session_cvr_pct": 0.0,
            "reserve_impact_top80_cvr_pct": round(cvr_reserve * 100, 4),
            "reserve_note": "Измерено в CH на top80 API-RESERVE: CVR=0%. В Δ RESERVE→точный: 0 → normal.",
            "avg_check_search_rub": aov_search,
            "avg_check_site_rub": aov_site,
            "search_revenue_90d": search_rev_90d,
            "site_orders_90d": 15580,
            "site_revenue_90d": 1720081481,
            "site_cvr_pct": 0.257,
            "caveat": (
                "В CH к поиску атрибуцируется мало заказов (1.3k из 15.5k). "
                "Для Δ используем search-session CVR нормальных сессий (0.083%) и AOV поиска (~100k ₽) — это консервативно."
            ),
        },
        "impact_pool_api": {
            "RESERVE": {"queries": reserve_q, "searches_90d": reserve_searches},
            "ZERO": {"queries": zero_q, "searches_90d": zero_searches},
            "NORMAL": {"queries": normal_q, "searches_90d": normal_searches},
        },
        "formula": (
            "ΔВыручка_90д = searches × fixable × (CVR_new − CVR_old) × AOV; "
            "месяц = /3. RESERVE→точный: CVR_measured(0%) → normal(0.083%). "
            "NORMAL→точный: +15…25% относительный lift на долю fixable. "
            "ZERO→найдено: 0 → 0.5×normal (консерв.)."
        ),
        "strategy_compare_sample": strat_cmp,
        "scenarios": results,
        "top_reserve_queries_money_base": top_rows,
        "partner_headline_base": results["base"]["calc"]["revenue_month"],
    }

    (OUT / "money_impact.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown for partner
    b = results["base"]["calc"]
    c = results["conservative"]["calc"]
    o = results["optimistic"]["calc"]
    md = []
    md.append("# ЦУМ — оценка прироста выручки от атрибутов с картинок\n")
    md.append("## Базовые метрики (ClickHouse, site 203, 90 дней)\n")
    md.append(f"- Сессии с поиском: **{overall['search_sessions']:,}**\n")
    md.append(f"- CVR точных (цель): **{cvr_normal*100:.3f}%** (normal-флаг {cvr_normal_flag*100:.3f}% / impact NORMAL top80 {cvr_normal_impact*100:.3f}%)\n")
    md.append(f"- CVR zero-флаг сессий: **0%**\n")
    md.append(f"- CVR запасных (измерено CH на API-RESERVE top80): **{cvr_reserve*100:.3f}%** → заказов 0\n")
    md.append(f"- Средний чек (заказы из search-сессий): **{aov_search:,.0f} ₽**\n")
    md.append(f"- Средний чек сайта: **{aov_site:,.0f} ₽**\n")
    md.append(f"- Выручка, атрибуцированная поиску: **{search_rev_90d:,.0f} ₽ / 90д**\n")
    md.append(f"- Выручка сайта: **1 720 081 481 ₽ / 90д**, CVR сайта **0.257%**\n")
    md.append(f"\n_{report['baselines_ch']['caveat']}_\n")
    md.append("\n## На какие запросы влияем (Diginetica API, vision-лексика)\n")
    md.append(f"| Тип | Запросов | Поисков / 90д |\n|---|---:|---:|\n")
    md.append(f"| **RESERVE (запасные)** | {reserve_q} | {reserve_searches:,} |\n")
    md.append(f"| ZERO (пустые) | {zero_q} | {zero_searches:,} |\n")
    md.append(f"| NORMAL (точные) | {normal_q} | {normal_searches:,} |\n")
    md.append(
        "\nCH `isZeroQuery` **не равен** API RESERVE: среди impact API дал **0 ZERO**, "
        "запасные собраны из API (`zeroQueries=true` при `totalHits>0`). "
        f"Расхождений CH↔API на выборке: **{api['summary'].get('ch_vs_api_disagree_n')}**.\n"
    )
    md.append("\n## Δ Выручка (₽)\n")
    md.append("| Сценарий | ₽/мес | ₽/90д | ₽/год |\n|---|---:|---:|---:|\n")
    md.append(f"| Консервативный | {c['revenue_month']['total']:,} | {c['revenue_90d']['total']:,} | {c['revenue_year']['total']:,} |\n")
    md.append(f"| **Базовый** | **{b['revenue_month']['total']:,}** | **{b['revenue_90d']['total']:,}** | **{b['revenue_year']['total']:,}** |\n")
    md.append(f"| Оптимистичный | {o['revenue_month']['total']:,} | {o['revenue_90d']['total']:,} | {o['revenue_year']['total']:,} |\n")
    md.append("\n### Базовый сценарий — разбивка\n")
    md.append(f"- RESERVE → точный: **{b['revenue_month']['reserve_to_exact']:,} ₽/мес**\n")
    md.append(f"- NORMAL → точнее: **{b['revenue_month']['normal_precision']:,} ₽/мес**\n")
    md.append(f"- ZERO → найдено: **{b['revenue_month']['zero_to_found']:,} ₽/мес**\n")
    md.append("\n## Топ запасных запросов (API) и вклад в Δ\n")
    md.append("| Запрос | Поисков/90д | hits API | ₽/мес (base) |\n|---|---:|---:|---:|\n")
    for r in top_rows[:20]:
        md.append(f"| {r['q']} | {r['searches_90d']} | {r['api_hits']} | {r['delta_rub_mo']:,} |\n")
    md.append(f"\n## Формула\n\n`{report['formula']}`\n")
    (OUT / "MONEY_IMPACT.md").write_text("".join(md), encoding="utf-8")

    print(json.dumps({
        "pool": report["impact_pool_api"],
        "base_month": b["revenue_month"],
        "conservative_month": c["revenue_month"]["total"],
        "optimistic_month": o["revenue_month"]["total"],
        "cvr_normal_pct": cvr_normal * 100,
        "aov_search": aov_search,
        "strat_cmp_n": len(strat_cmp),
    }, ensure_ascii=False, indent=2))
    print("Wrote money_impact.json + MONEY_IMPACT.md")


if __name__ == "__main__":
    main()
