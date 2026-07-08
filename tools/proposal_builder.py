#!/usr/bin/env python3
"""Generate partner proposal deck from Studio JSON + cases.yaml + MRR."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "decks/templates/partner-proposal.template.html"
CASES = ROOT / "portfolio/cases.yaml"
DEFAULT_DATA = ROOT / "decks/data/product-default.json"


def load_yaml(path: Path) -> list:
    if yaml is None:
        raise SystemExit("pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def recurring_pct(new_per_week: int) -> float:
    if new_per_week <= 500:
        return 5.0
    if new_per_week <= 2000:
        return 7.5
    return 10.0


def fmt_rub(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", " ") + " ₽"


def pick_cases(cases: list, vertical: str | None, limit: int = 3) -> list:
    scored = []
    for c in cases:
        if c.get("type") == "negative":
            continue
        score = c.get("slide_priority", 99)
        if vertical and c.get("vertical", "").lower() == vertical.lower():
            score -= 10
        scored.append((score, c))
    scored.sort(key=lambda x: x[0])
    return [c for _, c in scored[:limit]]


def cases_html(cases: list) -> str:
    parts = []
    for c in cases:
        m = c.get("metrics", {})
        headline = ""
        if "zero_queries_reduction_pct" in m:
            headline = f"Zero −{m['zero_queries_reduction_pct']}%"
        elif "ndcg_at_20_delta" in m:
            headline = f"NDCG +{m['ndcg_at_20_delta']}"
        elif "dashboard_rows" in m:
            headline = f"{m['dashboard_rows']} rows"
        elif "attrs_in_production" in m:
            headline = f"{m['attrs_in_production']} attrs"
        parts.append(
            f'<div class="glass fill-card" style="margin-bottom:12px">'
            f'<h3 class="card-h3">{c.get("vertical", "")} · {c.get("stream", "")}</h3>'
            f'<p><strong>{headline}</strong></p>'
            f'<p class="goal-note">{c.get("story", "").strip()[:200]}…</p></div>'
        )
    return "\n".join(parts) if parts else "<p class='glass'>Кейсы из portfolio/cases.yaml</p>"


def load_impact(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_deck_data(partner: str, site_id: int, mrr: float, impact: dict, cases: list) -> dict:
    base = json.loads(DEFAULT_DATA.read_text(encoding="utf-8"))
    base["meta"]["partner"] = partner
    base["meta"]["site_id"] = site_id
    base["pricing"] = {
        "mrr": mrr,
        "batch": mrr,
        "recurring_pct": recurring_pct(int(impact.get("new_per_week", 500))),
        "recurring": mrr * recurring_pct(int(impact.get("new_per_week", 500))) / 100,
    }
    if impact:
        base["partner_impact"] = {
            "zero_to_nonzero_freq": impact.get("zero_to_nonzero_freq", impact.get("zero_to_nonzero", "—")),
            "product_reach_rows": impact.get("product_reach_rows", "—"),
            "lexicon_gap_closure_pct": impact.get("lexicon_gap_closure_pct", impact.get("gap_closure_pct", "—")),
        }
    base["cases_selected"] = [c.get("id") for c in cases]
    return base


def main() -> None:
    ap = argparse.ArgumentParser(description="Build partner proposal HTML deck")
    ap.add_argument("--partner", required=True)
    ap.add_argument("--site-id", type=int, required=True)
    ap.add_argument("--mrr", type=float, required=True)
    ap.add_argument("--impact-json", type=Path, default=None)
    ap.add_argument("--vertical", default=None, help="Match cases by vertical")
    ap.add_argument("--new-per-week", type=int, default=500)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    cases_all = load_yaml(CASES)
    selected = pick_cases(cases_all, args.vertical, limit=3)
    impact_raw = load_impact(args.impact_json)
    impact = {**impact_raw, "new_per_week": args.new_per_week}

    pct = recurring_pct(args.new_per_week)
    deck_data = build_deck_data(args.partner, args.site_id, args.mrr, impact, selected)

    pi = deck_data.get("partner_impact", {})
    html = TEMPLATE.read_text(encoding="utf-8")
    repl = {
        "{{PARTNER}}": args.partner,
        "{{SITE_ID}}": str(args.site_id),
        "{{DATE}}": date.today().isoformat(),
        "{{ZERO_TO_NONZERO}}": str(pi.get("zero_to_nonzero_freq", "—")),
        "{{PRODUCT_REACH}}": str(pi.get("product_reach_rows", "—")),
        "{{LEXICON_GAP}}": str(pi.get("lexicon_gap_closure_pct", deck_data.get("lexicon", {}).get("closed_pct", "—"))),
        "{{CASES_HTML}}": cases_html(selected),
        "{{NDCG_HINT}}": "+0.003 … +9%",
        "{{ZERO_HINT}}": "до −33%",
        "{{BATCH_PRICE}}": fmt_rub(args.mrr),
        "{{MRR_FMT}}": fmt_rub(args.mrr),
        "{{RECURRING_PRICE}}": fmt_rub(args.mrr * pct / 100),
        "{{RECURRING_PCT}}": str(pct).replace(".0", ""),
        "{{DECK_DATA_JSON}}": json.dumps(deck_data, ensure_ascii=False),
    }
    for k, v in repl.items():
        html = html.replace(k, v)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
