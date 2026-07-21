"""ClickHouse filter impact metrics skeleton for partner reports.

Reuse 4lapy methodology:
  filter_lift_pp = conv_with_filters_pct - conv_without_filters_pct
  delta_revenue ≈ sessions × filter_share × max(0, lift_pp/100) × avg_check

For Zolla site_id=3826 — run when CH credentials point at that site.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def compute_filter_economics(
    *,
    category_sessions: int,
    filter_sessions: int,
    conv_with_filters_pct: float,
    conv_without_filters_pct: float,
    avg_check: float,
    assumed_filter_share: float | None = None,
) -> dict[str, Any]:
    lift_pp = round(conv_with_filters_pct - conv_without_filters_pct, 3)
    share = (
        assumed_filter_share
        if assumed_filter_share is not None
        else (filter_sessions / category_sessions if category_sessions else 0.0)
    )
    # monthly-ish if sessions already monthly; caller owns window
    delta = category_sessions * share * max(0.0, lift_pp / 100.0) * avg_check
    return {
        "filter_lift_pp": lift_pp,
        "filter_share": round(share, 4),
        "delta_revenue": round(delta, 2),
        "filters_per_query_proxy": round(filter_sessions / max(1, category_sessions), 4),
        "note": "measured lift; use max(0, lift) for upside forecast",
    }


def demo_from_4lapy_sample() -> dict[str, Any]:
    sample_path = ROOT / "portfolio" / "filter-conversion-data.json"
    if not sample_path.is_file():
        return {}
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    out = {}
    for cat, m in data.items():
        out[cat] = compute_filter_economics(
            category_sessions=int(m.get("category_sessions_events") or 0),
            filter_sessions=int(m.get("filter_sessions") or 0),
            conv_with_filters_pct=float(m.get("conv_with_filters_pct") or 0),
            conv_without_filters_pct=float(m.get("conv_without_filters_pct") or 0),
            avg_check=2117.0,
        )
    return out


def main() -> None:
    demo = demo_from_4lapy_sample()
    out = ROOT / "portfolio" / "zolla_filters" / "ch_metrics_demo.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "zolla_site_id": 3826,
        "status": "demo_formula_on_4lapy_sample — replace with CH pull for 3826",
        "demo": demo,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
