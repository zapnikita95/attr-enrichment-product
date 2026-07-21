# -*- coding: utf-8 -*-
"""Resume after vision: CH queries + money + HTML + Desktop Output."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _4lapy_vet_vision_research import (  # noqa: E402
    OUT,
    DESKTOP_OUT,
    FOCUS_IDS,
    pull_queries,
    compute_money,
    rank_attributes,
    build_html,
    cleanup_keeps,
)

inv = json.loads((OUT / "feed_inventory_vet.json").read_text(encoding="utf-8"))
results = cleanup_keeps(
    json.loads((OUT / "vision_results.json").read_text(encoding="utf-8"))
)
(OUT / "vision_results_clean.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
ranking = rank_attributes(results)
(OUT / "attr_ranking.json").write_text(
    json.dumps(ranking, ensure_ascii=False, indent=2), encoding="utf-8"
)

print("CH…")
qdata = pull_queries()
(OUT / "query_impact_vet.json").write_text(
    json.dumps(qdata, ensure_ascii=False, indent=2), encoding="utf-8"
)
money = compute_money(qdata, ranking)
(OUT / "money_vet.json").write_text(
    json.dumps(money, ensure_ascii=False, indent=2), encoding="utf-8"
)

focus_cases = [r for r in results if r.get("id") in FOCUS_IDS]
html = build_html(inv, qdata, money, results, ranking, focus_cases)
html_path = OUT / "4lapy-vet-pharmacy-image-attrs.html"
html_path.write_text(html, encoding="utf-8")

DESKTOP_OUT.mkdir(parents=True, exist_ok=True)
(DESKTOP_OUT / "4lapy-vet-pharmacy-image-attrs.html").write_text(html, encoding="utf-8")

summary = {
    "focus_ids": FOCUS_IDS,
    "vision_n": len(results),
    "keep_total": sum(len(r.get("keep") or []) for r in results),
    "money_base_a_month": money["scenarios"]["base"]["stream_a_month"],
    "money_b_cons_opt_month": [
        money["scenarios"]["conservative"]["stream_b_month"],
        money["scenarios"]["optimistic"]["stream_b_month"],
    ],
    "baseline": money["baseline"],
    "vet_searches_90d": qdata["vet_related_searches"],
    "top_attrs": ranking[:12],
    "focus_keep": {
        r["id"]: [{"name": a.get("name"), "value": a.get("value")} for a in (r.get("keep") or [])]
        for r in focus_cases
    },
    "html": str(html_path),
    "desktop": str(DESKTOP_OUT / "4lapy-vet-pharmacy-image-attrs.html"),
}
(OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
(DESKTOP_OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

md = [
    "# 4lapy ветаптека — заключение\n\n",
    f"- Vision: **{len(results)}** упаковок\n",
    f"- KEEP атрибутов: **{summary['keep_total']}**\n",
    f"- Вет/паразит поиск 90д: **{qdata['vet_related_searches']:,}**\n",
    f"- Search CVR: **{money['baseline']['search_cvr_pct']}%**, AOV **{money['baseline']['aov']:,.0f} ₽**\n",
    f"- Стрим A (база): **{summary['money_base_a_month']:,} ₽/мес**\n",
    f"- Стрим B (доп.): **+{summary['money_b_cons_opt_month'][0]:,}…+{summary['money_b_cons_opt_month'][1]:,} ₽/мес**\n\n",
    "## Focus SKU\n\n",
]
for oid, attrs in summary["focus_keep"].items():
    md.append(f"### {oid}\n")
    for a in attrs:
        md.append(f"- {a['name']}: {a['value']}\n")
    md.append("\n")
md.append("## Топ атрибутов по эффекту\n\n")
for r in ranking[:10]:
    md.append(f"- **{r['attr']}** ({r['effectiveness']}) — {r['n_products']} SKU\n")
(OUT / "SUMMARY.md").write_text("".join(md), encoding="utf-8")
(DESKTOP_OUT / "SUMMARY.md").write_text("".join(md), encoding="utf-8")

print(json.dumps(summary, ensure_ascii=False, indent=2))
