# -*- coding: utf-8 -*-
"""Recalc TSUM money using Metrika search CVR/AOV + API reserve/normal pools."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"


def main() -> None:
    m = json.loads((OUT / "metrika_cvr_clean.json").read_text(encoding="utf-8"))
    api = json.loads((OUT / "api_classify_impact.json").read_text(encoding="utf-8"))
    kinds = api["summary"]["by_kind"]

    cvr_normal = m["with_search"]["cvr_pct"] / 100.0  # ~1.21%
    cvr_reserve = 0.0  # measured CH on API-reserve; keep 0 or half — use 0.35*normal as mid
    # Partner honesty: reserve shows products → not pure zero. Use 40% of search CVR as current.
    cvr_reserve_assumed = cvr_normal * 0.40
    aov = m["with_search"]["aov"]  # ~107k

    reserve_s = int(kinds.get("RESERVE", {}).get("searches_90d") or 0)
    normal_s = int(kinds.get("NORMAL", {}).get("searches_90d") or 0)
    zero_s = int(kinds.get("ZERO", {}).get("searches_90d") or 0)

    scenarios = {
        "conservative": {
            "reserve_fixable": 0.70,
            "normal_fixable": 0.25,
            "normal_rel_lift": 0.15,
            "reserve_old": cvr_reserve_assumed,
            "reserve_new": cvr_normal,
            "aov": aov,
        },
        "base": {
            "reserve_fixable": 0.80,
            "normal_fixable": 0.35,
            "normal_rel_lift": 0.20,
            "reserve_old": cvr_reserve_assumed,
            "reserve_new": cvr_normal,
            "aov": aov,
        },
        "optimistic": {
            "reserve_fixable": 0.90,
            "normal_fixable": 0.45,
            "normal_rel_lift": 0.25,
            "reserve_old": cvr_reserve,  # 0 measured
            "reserve_new": cvr_normal,
            "aov": m["overall"]["aov"],
        },
    }

    out_sc = {}
    for name, sc in scenarios.items():
        d_r = sc["reserve_new"] - sc["reserve_old"]
        rev_r_90 = reserve_s * sc["reserve_fixable"] * d_r * sc["aov"]
        d_n = cvr_normal * sc["normal_rel_lift"]
        rev_n_90 = normal_s * sc["normal_fixable"] * d_n * sc["aov"]
        total_90 = rev_r_90 + rev_n_90
        out_sc[name] = {
            "revenue_90d": {
                "reserve_to_exact": round(rev_r_90),
                "normal_precision": round(rev_n_90),
                "total": round(total_90),
            },
            "revenue_month": {
                "reserve_to_exact": round(rev_r_90 / 3),
                "normal_precision": round(rev_n_90 / 3),
                "total": round(total_90 / 3),
            },
            "revenue_year": {"total": round(total_90 / 3 * 12)},
            "params": {
                "cvr_normal_pct": round(cvr_normal * 100, 3),
                "cvr_reserve_old_pct": round(sc["reserve_old"] * 100, 3),
                "aov": round(sc["aov"]),
                "reserve_searches_90d": reserve_s,
                "normal_searches_90d": normal_s,
            },
        }

    report = {
        "source_cvr": "Yandex Metrika goal 260498358 (Автоцель: поиск по сайту)",
        "metrika": {
            "cvr_with_search_pct": m["with_search"]["cvr_pct"],
            "cvr_without_search_pct": m["without_search"]["cvr_pct"],
            "aov_with_search": m["with_search"]["aov"],
            "aov_site": m["overall"]["aov"],
            "lift_x": m["search_vs_no_lift_x"],
        },
        "vs_ch": {
            "ch_search_cvr_pct": 0.083,
            "metrika_search_cvr_pct": round(cvr_normal * 100, 3),
            "note": "CH занижал search CVR; для партнёра берём Метрику",
        },
        "pool": {
            "RESERVE": {"searches_90d": reserve_s, "queries": kinds.get("RESERVE", {}).get("queries")},
            "NORMAL": {"searches_90d": normal_s, "queries": kinds.get("NORMAL", {}).get("queries")},
            "ZERO": {"searches_90d": zero_s},
        },
        "scenarios": out_sc,
        "formula": "Δ90д = searches × fixable × ΔCVR × AOV_metrika; мес=/3",
    }
    (OUT / "money_impact_metrika.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    b = out_sc["base"]
    c = out_sc["conservative"]
    o = out_sc["optimistic"]
    md = []
    md.append("# ЦУМ — деньги на конверсии из Яндекс.Метрики\n\n")
    md.append("## Проверка API\n")
    md.append(f"- Счётчик **{m['counter_id']}** ({m.get('counter_name')}) · сайт `{m.get('site')}` — **OK**\n")
    md.append(f"- Ecommerce 90д: CVR сайта **{m['overall']['cvr_pct']:.3f}%**, AOV **{m['overall']['aov']:,.0f} ₽**\n")
    md.append(
        f"- Цель поиска `{m['search_goal_id']}`: CVR с поиском **{m['with_search']['cvr_pct']:.3f}%** "
        f"(AOV **{m['with_search']['aov']:,.0f} ₽**) vs без поиска **{m['without_search']['cvr_pct']:.3f}%** "
        f"→ ×**{m['search_vs_no_lift_x']:.2f}**\n"
    )
    md.append(f"- Diginetica CH search CVR был **0.083%** — для ₽ не используем.\n\n")
    md.append("## Δ выручка\n\n")
    md.append("| Сценарий | ₽/мес | ₽/90д | ₽/год |\n|---|---:|---:|---:|\n")
    md.append(f"| Консервативный | {c['revenue_month']['total']:,} | {c['revenue_90d']['total']:,} | {c['revenue_year']['total']:,} |\n")
    md.append(f"| **Базовый** | **{b['revenue_month']['total']:,}** | **{b['revenue_90d']['total']:,}** | **{b['revenue_year']['total']:,}** |\n")
    md.append(f"| Оптимистичный | {o['revenue_month']['total']:,} | {o['revenue_90d']['total']:,} | {o['revenue_year']['total']:,} |\n")
    md.append("\n### Базовый\n")
    md.append(f"- RESERVE→точный: **{b['revenue_month']['reserve_to_exact']:,} ₽/мес**\n")
    md.append(f"- NORMAL точнее: **{b['revenue_month']['normal_precision']:,} ₽/мес**\n")
    (OUT / "MONEY_IMPACT.md").write_text("".join(md), encoding="utf-8")

    # also refresh money_impact.json headline for HTML
    old_money = {}
    mp = OUT / "money_impact.json"
    if mp.exists():
        old_money = json.loads(mp.read_text(encoding="utf-8"))
    old_money["metrika_recalc"] = report
    old_money["partner_headline_base"] = b["revenue_month"]
    old_money["baselines_ch"]["caveat"] = (
        "Устарело для денег: используйте metrika_recalc / MONEY_IMPACT.md (Метрика CVR ~1.21%)."
    )
    mp.write_text(json.dumps(old_money, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "base_month": b["revenue_month"]["total"],
        "conservative_month": c["revenue_month"]["total"],
        "optimistic_month": o["revenue_month"]["total"],
        "cvr_search": round(cvr_normal * 100, 3),
        "aov": round(aov),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
