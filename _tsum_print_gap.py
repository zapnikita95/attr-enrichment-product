# -*- coding: utf-8 -*-
import json
from pathlib import Path

p = Path(__file__).resolve().parent / "portfolio" / "tsum" / "gap_analysis.json"
print("exists", p.exists(), "size", p.stat().st_size if p.exists() else 0)
d = json.loads(p.read_text(encoding="utf-8"))
for fam, info in sorted(d["needle_families"].items(), key=lambda x: -x[1]["searches_90d"]):
    res = d["needle_families_residual_searches"].get(fam)
    print(f"{fam:25} q={info['unique_queries']:4} searches={info['searches_90d']:8} residual={res}")
print("--- top vision gap ---")
for r in d["top_vision_gap_queries"][:30]:
    print(r["cnt"], r["q"], "missing=", r["missing_tokens"][:6])
print("--- family examples material ---")
for fam in ["pattern_print", "silhouette_fit", "perfume_notes", "bag_type", "shoe_details"]:
    print(fam, d["needle_families"][fam]["examples"][:5])
