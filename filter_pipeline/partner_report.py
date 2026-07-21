"""Partner-facing HTML: filters by category + pilot metrics (+ CH placeholder)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def build_html(out_dir: Path) -> Path:
    schema = {}
    schema_path = out_dir / "filter_schema_clean.json"
    if not schema_path.is_file():
        schema_path = out_dir / "filter_schema.json"
    if schema_path.is_file():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

    vision = {}
    vs = out_dir / "vision_summary.json"
    if vs.is_file():
        vision = json.loads(vs.read_text(encoding="utf-8"))

    text_stats = {}
    tm = out_dir / "text_mapped.json"
    if tm.is_file():
        text_stats = json.loads(tm.read_text(encoding="utf-8")).get("stats") or {}

    compare = {}
    cp = out_dir / "model_compare.json"
    if cp.is_file():
        compare = json.loads(cp.read_text(encoding="utf-8"))

    attrs = schema.get("attributes") or []
    rows_html = ""
    for a in attrs:
        rows_html += (
            f"<tr><td>{a.get('label_ru')}</td><td><code>{a.get('attr_id')}</code></td>"
            f"<td>{a.get('value_type')}</td><td>{', '.join(a.get('allowed_values') or [])}</td>"
            f"<td>{', '.join(a.get('categories') or [])}</td>"
            f"<td>{a.get('why_filter') or ''}</td></tr>"
        )

    vis_rows = ""
    for aid, s in vision.items():
        vis_rows += (
            f"<tr><td>{aid}</td><td>{s.get('model')}</td><td>{s.get('n')}</td>"
            f"<td>{s.get('coerced_rate')}</td><td>{s.get('expected_match_rate')}</td>"
            f"<td>{s.get('ood_or_fail')}</td></tr>"
        )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<title>Zolla — Filter Enrichment Pilot</title>
<style>
  body {{ font-family: "Segoe UI", system-ui, sans-serif; margin: 2rem; background: #0d1117; color: #e6edf3; }}
  h1,h2 {{ color: #f0f6fc; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0 2rem; }}
  th,td {{ border: 1px solid #30363d; padding: 0.5rem 0.75rem; text-align: left; vertical-align: top; }}
  th {{ background: #161b22; }}
  code {{ color: #79c0ff; }}
  .muted {{ color: #8b949e; }}
  .card {{ background: #161b22; border: 1px solid #30363d; padding: 1rem 1.25rem; margin: 1rem 0; border-radius: 6px; }}
</style>
</head>
<body>
<h1>Zolla — фильтры из описаний и картинок</h1>
<p class="muted">Pilot report · {ts} · site_id 3826</p>

<div class="card">
  <h2>Методология</h2>
  <ol>
    <li>Filter candidacy (LLM): filter vs search-only vs reject</li>
    <li>Schema: value_type + closed allowed_values</li>
    <li>Typed extract (vision OpenRouter / text gold) — только канон</li>
    <li>Hard coerce + feed collision</li>
    <li>Impact: coverage × query demand × CR with/without filters (ClickHouse)</li>
  </ol>
  <p>Search lexicon и facet-фильтры считаются <b>отдельно</b>.</p>
</div>

<h2>Фильтры по схеме</h2>
<table>
<thead><tr><th>Фильтр</th><th>id</th><th>Тип</th><th>Allowed</th><th>Категории</th><th>Почему фильтр</th></tr></thead>
<tbody>{rows_html or "<tr><td colspan=6>schema pending</td></tr>"}</tbody>
</table>

<h2>Vision pilot (OpenRouter)</h2>
<table>
<thead><tr><th>attr</th><th>model</th><th>n</th><th>coerced_rate</th><th>expected_match</th><th>fail</th></tr></thead>
<tbody>{vis_rows or "<tr><td colspan=6>vision pending</td></tr>"}</tbody>
</table>

<h2>Text gold coerce (3826)</h2>
<pre>{json.dumps(text_stats, ensure_ascii=False, indent=2)}</pre>

<h2>Model bakeoff</h2>
<pre>{json.dumps(compare, ensure_ascii=False, indent=2)}</pre>

<div class="card">
  <h2>ClickHouse impact (next)</h2>
  <p>Метрики для партнёра (после появления facet usage / или baseline категории):</p>
  <ul>
    <li><code>conv_with_filters_pct</code> vs <code>conv_without_filters_pct</code> → <code>filter_lift_pp</code></li>
    <li>SKU coverage по каждому facet</li>
    <li>доля search sessions с ≥1 filter</li>
    <li>filters per query</li>
    <li>Δвыручка = sessions × filter_share × max(0, lift_pp) × avg_check</li>
  </ul>
  <p class="muted">Скелет как в 4lapy <code>filter-conversion-data.json</code>. Для Zolla site_id=3826 нужен CH pull.</p>
</div>
</body>
</html>
"""
    path = out_dir / "zolla-filter-impact.html"
    path.write_text(html, encoding="utf-8")
    return path
