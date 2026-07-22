# -*- coding: utf-8 -*-
"""Пересчитать KEEP/REJECT без повторного vision + обновить HTML/Desktop."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from _4lapy_vet_vision_research import (
    DESKTOP_OUT,
    FOCUS_IDS,
    OUT,
    build_html,
    cleanup_keeps,
    compute_money,
    rank_attributes,
)

raw = json.loads((OUT / "vision_results.json").read_text(encoding="utf-8"))
# подтянуть vendor/brand из focus/sample если пусто
sample = {}
for p in (OUT / "vision_sample.json", OUT / "focus_offers.json"):
    if not p.exists():
        continue
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        for o in data:
            sample[str(o.get("id"))] = o
    elif isinstance(data, dict):
        for k, o in data.items():
            if isinstance(o, dict):
                sample[str(k)] = o

for r in raw:
    o = sample.get(str(r.get("id"))) or {}
    if not r.get("vendor") and o.get("vendor"):
        r["vendor"] = o["vendor"]
    if not r.get("brand"):
        r["brand"] = r.get("vendor") or o.get("brand") or ((r.get("name") or "").split() or [""])[0]
    if not r.get("category_path") and o.get("category_path"):
        r["category_path"] = o["category_path"]

results = cleanup_keeps(raw)
(OUT / "vision_results.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "vision_results_clean.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)

ranking = rank_attributes(results)
(OUT / "attr_ranking.json").write_text(json.dumps(ranking, ensure_ascii=False, indent=2), encoding="utf-8")

inv = json.loads((OUT / "feed_inventory_vet.json").read_text(encoding="utf-8"))
qdata = json.loads((OUT / "query_impact_vet.json").read_text(encoding="utf-8"))
money = compute_money(qdata, ranking)
(OUT / "money_vet.json").write_text(json.dumps(money, ensure_ascii=False, indent=2), encoding="utf-8")

focus_cases = [r for r in results if r.get("id") in FOCUS_IDS]
html = build_html(inv, qdata, money, results, ranking, focus_cases)
html_path = OUT / "4lapy-vet-pharmacy-image-attrs.html"
html_path.write_text(html, encoding="utf-8")

DESKTOP_OUT.mkdir(parents=True, exist_ok=True)
(DESKTOP_OUT / "4lapy-vet-pharmacy-image-attrs.html").write_text(html, encoding="utf-8")

keep_total = sum(len(r.get("keep") or []) for r in results)
focus_keep = {
    r["id"]: [{"name": a.get("name"), "value": a.get("value")} for a in (r.get("keep") or [])]
    for r in focus_cases
}
summary = {
    "focus_ids": FOCUS_IDS,
    "vision_n": len(results),
    "keep_total": keep_total,
    "focus_keep": focus_keep,
    "note": "collision reprocess: name/category/brand/params + form synonyms",
    "html": str(html_path),
    "desktop": str(DESKTOP_OUT / "4lapy-vet-pharmacy-image-attrs.html"),
}
# merge money fields if previous SUMMARY exists
prev = {}
if (OUT / "SUMMARY.json").exists():
    prev = json.loads((OUT / "SUMMARY.json").read_text(encoding="utf-8"))
summary = {**prev, **summary, "top_attrs": ranking[:12]}
(OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
(DESKTOP_OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

md = [
    "# 4lapy ветаптека — заключение\n\n",
    f"- Vision: **{len(results)}** упаковок\n",
    f"- KEEP атрибутов: **{keep_total}** (после жёсткой коллизии с фидом)\n",
    "## Focus SKU\n\n",
]
for fid in FOCUS_IDS:
    md.append(f"### {fid}\n")
    for a in focus_keep.get(fid) or []:
        md.append(f"- {a['name']}: {a['value']}\n")
    md.append("\n")
(OUT / "SUMMARY.md").write_text("".join(md), encoding="utf-8")
(DESKTOP_OUT / "SUMMARY.md").write_text("".join(md), encoding="utf-8")

# audit print
print("keep_total", keep_total)
for fid in FOCUS_IDS:
    print(fid, focus_keep.get(fid))
# spot-check imid / spot-on
for r in results:
    if r.get("id") == "1029780":
        print("1029780 keep:", [(a.get("name"), a.get("value")) for a in r.get("keep") or []])
        print("1029780 reject reasons:", [(a.get("value"), a.get("reason")) for a in r.get("reject") or []])
