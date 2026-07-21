import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "portfolio" / "zolla_filters"
summary = {}
for p in OUT.glob("vision_*.json"):
    if "compare" in p.name or p.name == "vision_summary.json":
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    aid = d.get("attr_id") or p.stem.replace("vision_", "")
    summary[aid] = {
        k: d[k]
        for k in (
            "attr_id",
            "model",
            "n",
            "coerced_ok",
            "coerced_rate",
            "expected_match",
            "expected_match_rate",
            "ood_or_fail",
        )
        if k in d
    }
(OUT / "vision_summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(summary, ensure_ascii=False, indent=2))
tm = json.loads((OUT / "text_mapped.json").read_text(encoding="utf-8"))
print("text", tm.get("stats"))
