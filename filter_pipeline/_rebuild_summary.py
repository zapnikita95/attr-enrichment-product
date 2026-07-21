import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "portfolio" / "zolla_filters"
summary = {}
for p in sorted(OUT.glob("vision_*.json")):
    if p.name == "vision_summary.json" or "unique" in p.name or "compare" in p.name:
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    aid = d.get("attr_id") or p.stem.replace("vision_", "")
    summary[aid] = {
        "attr_id": aid,
        "model": d.get("model"),
        "n_unique_pics": d.get("n_unique_pics", d.get("n")),
        "n_offers": d.get("n_offers", len(d.get("rows") or [])),
        "n_propagated": d.get("n_propagated", 0),
        "coerced_ok": d.get("coerced_ok"),
        "coerced_rate": d.get("coerced_rate"),
        "expected_match": d.get("expected_match"),
        "expected_match_rate": d.get("expected_match_rate"),
        "ood_or_fail": d.get("ood_or_fail"),
    }
(OUT / "vision_summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(summary, ensure_ascii=False, indent=2))
for aid, s in summary.items():
    u = s.get("n_unique_pics") or 0
    o = s.get("n_offers") or 0
    print(f"{aid}: unique={u} offers={o} saved={max(0, o - u)}")

from filter_pipeline.run_zolla_pilot import write_detailed_results

write_detailed_results()
