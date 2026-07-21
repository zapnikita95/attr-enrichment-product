# -*- coding: utf-8 -*-
import json
from pathlib import Path

d = json.loads(
    (Path(__file__).resolve().parent / "portfolio/tsum/pattern_name_coverage.json").read_text(
        encoding="utf-8"
    )
)
print("UNION", json.dumps(d["union_any_needle"], ensure_ascii=False, indent=2))
print()
for n, x in sorted(d["per_needle"].items(), key=lambda kv: -kv[1]["in_name"]):
    if x["in_name"] or x["in_params"] or x["in_attribute_details"]:
        print(
            f"{n:12} name={x['in_name']:5} ({x['name_pct']}%)  "
            f"params={x['in_params']:5} ({x['params_pct']}%)  "
            f"details={x['in_attribute_details']:4}  custom={x['in_custom_categories']:5}  "
            f"name_only={x['name_only_not_in_params']:4}"
        )
