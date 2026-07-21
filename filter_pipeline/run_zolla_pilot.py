#!/usr/bin/env python3
"""Zolla filter pipeline pilot — real OpenRouter prompts per stage.

Usage:
  py -3.13 filter_pipeline/run_zolla_pilot.py --stage all
  py -3.13 filter_pipeline/run_zolla_pilot.py --stage vision --attrs hood,length,print_pattern
  py -3.13 filter_pipeline/run_zolla_pilot.py --stage compare_models --attrs hood
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from filter_pipeline.candidacy import run_candidacy
from filter_pipeline.dedupe import propagate_rows, unique_representatives
from filter_pipeline.extract_text import map_gold_to_filters
from filter_pipeline.extract_vision import run_extract_batch
from filter_pipeline.llm_client import (
    COMPARE_VISION_MODELS,
    DEFAULT_TEXT_MODEL,
    DEFAULT_VISION_MODEL,
    MODEL_COST_NOTES,
    vision_model_for_attr,
)
from filter_pipeline.models import FASHION_SEED_SPECS, FilterAttributeSpec
from filter_pipeline.samples import dump_samples
from filter_pipeline.schema_stage import load_specs, run_schema_stage

DEFAULT_ATTRS = (
    "hood,length,print_pattern,sleeve_length,pockets,fastener,collar"
)

OUT = ROOT / "portfolio" / "zolla_filters"
OBS = Path(__file__).resolve().parent / "observations.md"


def _append_obs(section: str, body: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block = f"\n## {section} ({ts})\n\n{body.strip()}\n"
    if OBS.exists():
        OBS.write_text(OBS.read_text(encoding="utf-8") + block, encoding="utf-8")
    else:
        OBS.write_text("# Zolla Filter Pipeline — Observations\n" + block, encoding="utf-8")


def stage_samples() -> dict:
    path = OUT / "pilot_samples.json"
    data = dump_samples(path)
    print(f"samples → {path}")
    for k, v in data.items():
        print(f"  {k}: {len(v)}")
    return data


def stage_candidacy(model: str) -> dict:
    candidates = [
        {
            "name": s.label_ru,
            "attr_id": s.attr_id,
            "example_values": s.allowed_values[:6],
            "notes": s.why_filter,
        }
        for s in FASHION_SEED_SPECS
    ]
    # Add a few reject/search traps for the LLM to classify
    candidates.extend(
        [
            {
                "name": "Ощущение ткани",
                "example_values": ["мягкий", "приятный к телу"],
                "notes": "маркетинг",
            },
            {
                "name": "Состав детальный",
                "example_values": ["62% хлопок 38% полиэстер"],
                "notes": "высокая кардинальность",
            },
            {
                "name": "Цвет",
                "example_values": ["чёрный", "бежевый", "мультиколор"],
                "notes": "часто уже в фиде / отдельный системный facet",
            },
            {
                "name": "Описание ощущения/эффекта",
                "example_values": ["мягкий к телу", "эффект стройности"],
                "notes": "маркетинг",
            },
            {
                "name": "Размер",
                "example_values": ["S", "M", "42", "44"],
                "notes": "уже в фиде как variant",
            },
        ]
    )
    print(f"[candidacy] model={model}")
    result = run_candidacy(
        candidates,
        categories=["верхняя_одежда", "платья", "футболки_топы"],
        model=model,
        out_path=OUT / "filter_candidates.json",
    )
    decisions = (result.get("parsed") or {}).get("decisions") or []
    lines = [f"- model: `{model}`", f"- decisions: {len(decisions)}"]
    for d in decisions:
        lines.append(
            f"- **{d.get('name')}** → `{d.get('role')}` ({d.get('suggested_value_type')}): {d.get('why')}"
        )
    _append_obs("Stage 2 — Filter candidacy", "\n".join(lines))
    print(json.dumps(result.get("parsed"), ensure_ascii=False, indent=2)[:2000])
    return result


def stage_schema(model: str) -> dict:
    print(f"[schema] model={model}")
    result = run_schema_stage(model=model, out_path=OUT / "filter_schema.json")
    attrs = result.get("attributes") or []
    lines = [f"- model: `{model}`", f"- attrs: {len(attrs)}"]
    for a in attrs:
        lines.append(
            f"- **{a.get('attr_id')}** `{a.get('value_type')}` allowed={a.get('allowed_values')}"
        )
    _append_obs("Stage 3 — Type + vocabulary", "\n".join(lines))
    print("schema attrs:", [a.get("attr_id") for a in attrs])
    return result


def _spec_by_id(attr_id: str, schema_path: Path) -> FilterAttributeSpec:
    if schema_path.is_file():
        for s in load_specs(schema_path):
            if s.attr_id == attr_id:
                # merge seed synonyms if LLM omitted
                for seed in FASHION_SEED_SPECS:
                    if seed.attr_id == attr_id:
                        syn = dict(seed.synonym_map)
                        syn.update(s.synonym_map or {})
                        s.synonym_map = syn
                        if not s.allowed_values:
                            s.allowed_values = list(seed.allowed_values)
                        break
                return s
    for s in FASHION_SEED_SPECS:
        if s.attr_id == attr_id:
            return s
    raise KeyError(attr_id)


def stage_vision(
    attrs: list[str],
    model: str | None = None,
    samples_data: dict | None = None,
) -> dict:
    samples_data = samples_data or json.loads((OUT / "pilot_samples.json").read_text(encoding="utf-8"))
    schema_path = OUT / "filter_schema.json"
    summaries = {}
    for attr_id in attrs:
        spec = _spec_by_id(attr_id, schema_path)
        samples = samples_data.get(attr_id) or []
        usable = [s for s in samples if s.get("local_image") or s.get("picture_url")]
        # NEVER call vision twice for the same picture — then propagate to siblings
        reps = unique_representatives(usable)
        use_model = vision_model_for_attr(attr_id, model)
        print(
            f"[vision] {attr_id} offers={len(usable)} unique_pics={len(reps)} "
            f"saved_calls={len(usable) - len(reps)} model={use_model}"
        )
        if not reps:
            print("  SKIP no images")
            continue
        summary = run_extract_batch(
            spec,
            reps,
            model=use_model,
            out_path=OUT / f"vision_{attr_id}_unique.json",
        )
        expanded = propagate_rows(summary["rows"])
        n_prop = sum(1 for r in expanded if r.get("propagated"))
        summary["rows_unique"] = summary["rows"]
        summary["rows"] = expanded
        summary["n_offers"] = len(expanded)
        summary["n_unique_pics"] = len(reps)
        summary["n_propagated"] = n_prop
        (OUT / f"vision_{attr_id}.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summaries[attr_id] = {
            "attr_id": attr_id,
            "model": use_model,
            "n_unique_pics": len(reps),
            "n_offers": len(expanded),
            "n_propagated": n_prop,
            "coerced_ok": summary["coerced_ok"],
            "coerced_rate": summary["coerced_rate"],
            "expected_match": summary.get("expected_match"),
            "expected_match_rate": summary.get("expected_match_rate"),
            "ood_or_fail": summary["ood_or_fail"],
        }
        bad_raw = []
        for r in summary["rows_unique"]:
            rv = str(r.get("raw_value") or "")
            if not r.get("coerced_ok"):
                bad_raw.append(
                    f"{r.get('offer_id')}: FAIL raw={rv!r} reason={r.get('coerce_reason') or r.get('error')}"
                )
            elif rv and rv not in (spec.allowed_values or []) and str(r.get("coerced_value")) != rv:
                bad_raw.append(f"{r.get('offer_id')}: {rv!r} → {r.get('coerced_value')!r}")
        body = (
            f"- model: `{use_model}` (budget default)\n"
            f"- unique_pics: {len(reps)} / offers: {len(expanded)} (propagated {n_prop})\n"
            f"- coerced_rate: {summary['coerced_rate']} ({summary['coerced_ok']}/{summary['n']})\n"
            f"- expected_match_rate: {summary.get('expected_match_rate')}\n"
            f"- issues:\n" + ("\n".join(f"  - {x}" for x in bad_raw[:30]) or "  - none")
        )
        _append_obs(f"Stage 4 — Vision typed extract `{attr_id}`", body)
    (OUT / "vision_summary.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summaries


def stage_compare_models(attrs: list[str], samples_data: dict | None = None) -> dict:
    """Cheap bakeoff: gemma vs flash-lite on unique pics only (max 4)."""
    samples_data = samples_data or json.loads((OUT / "pilot_samples.json").read_text(encoding="utf-8"))
    schema_path = OUT / "filter_schema.json"
    report: dict = {"cost_notes": MODEL_COST_NOTES, "attrs": {}}
    for attr_id in attrs:
        spec = _spec_by_id(attr_id, schema_path)
        usable = [s for s in (samples_data.get(attr_id) or []) if s.get("local_image") or s.get("picture_url")]
        samples = unique_representatives(usable)[:4]
        per_model = {}
        for model in COMPARE_VISION_MODELS:
            print(f"[compare] {attr_id} n={len(samples)} model={model}")
            try:
                summary = run_extract_batch(
                    spec,
                    samples,
                    model=model,
                    out_path=OUT / f"compare_{attr_id}_{model.replace('/', '_')}.json",
                )
                per_model[model] = {
                    "coerced_rate": summary["coerced_rate"],
                    "expected_match_rate": summary.get("expected_match_rate"),
                    "n": summary["n"],
                    "tier": (MODEL_COST_NOTES.get(model) or {}).get("tier"),
                }
            except Exception as e:
                per_model[model] = {"error": str(e)}
        best = max(
            (m for m, v in per_model.items() if "coerced_rate" in v),
            key=lambda m: (
                per_model[m].get("expected_match_rate") or 0,
                per_model[m].get("coerced_rate") or 0,
            ),
            default=None,
        )
        report["attrs"][attr_id] = {"models": per_model, "best": best}
        _append_obs(
            f"Model bakeoff `{attr_id}` (cheap)",
            json.dumps(report["attrs"][attr_id], ensure_ascii=False, indent=2),
        )
    (OUT / "model_compare.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def stage_text() -> dict:
    schema_path = OUT / "filter_schema.json"
    specs = load_specs(schema_path) if schema_path.is_file() else list(FASHION_SEED_SPECS)
    print("[text] map gold 3826 → filter schema")
    result = map_gold_to_filters(specs, out_path=OUT / "text_mapped.json")
    _append_obs("Stage 4b — Text gold coerce", json.dumps(result.get("stats"), ensure_ascii=False, indent=2))
    print("stats", result.get("stats"))
    return result


def stage_report() -> Path:
    from filter_pipeline.partner_report import build_html

    path = build_html(OUT)
    _append_obs("Stage 6 — Partner HTML", f"Wrote `{path}`")
    write_detailed_results()
    return path


def write_detailed_results() -> Path:
    """Human-readable итоги: сделано / осталось / модели / дедуп."""
    schema = {}
    sp = OUT / "filter_schema_clean.json"
    if sp.is_file():
        schema = json.loads(sp.read_text(encoding="utf-8"))
    elif (OUT / "filter_schema.json").is_file():
        schema = json.loads((OUT / "filter_schema.json").read_text(encoding="utf-8"))
    cand = {}
    if (OUT / "filter_candidates.json").is_file():
        cand = json.loads((OUT / "filter_candidates.json").read_text(encoding="utf-8"))
    vision = {}
    if (OUT / "vision_summary.json").is_file():
        vision = json.loads((OUT / "vision_summary.json").read_text(encoding="utf-8"))
    compare = {}
    if (OUT / "model_compare.json").is_file():
        compare = json.loads((OUT / "model_compare.json").read_text(encoding="utf-8"))
    text_stats = {}
    if (OUT / "text_mapped.json").is_file():
        text_stats = json.loads((OUT / "text_mapped.json").read_text(encoding="utf-8")).get("stats") or {}

    decisions = (cand.get("parsed") or {}).get("decisions") or []
    done_attrs = [a for a, s in vision.items() if (s.get("coerced_rate") or 0) >= 0.9]
    weak_attrs = [a for a, s in vision.items() if (s.get("coerced_rate") or 0) < 0.9]
    schema_ids = [a.get("attr_id") for a in (schema.get("attributes") or [])]

    lines = [
        "# Zolla Filter Pipeline — DETAILED RESULTS",
        "",
        f"Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Budget models (defaults)",
        "",
        "- Text (candidacy/schema): `google/gemini-2.5-flash-lite`",
        "- Vision bulk: `google/gemma-3-4b-it`",
        "- Lurex verify only: `google/gemini-2.5-flash-lite` (optional, FILTER_LUREX_VERIFY=0 to skip)",
        "- Premium `gemini-2.5-flash` / `gpt-4o-mini` — только research, не bulk",
        "",
        "## Model research (как работают)",
        "",
        "### Previous premium bakeoff (hood / pattern)",
        "",
        "| Model | tier | hood boolean | print_pattern notes |",
        "|-------|------|--------------|---------------------|",
        "| gemini-2.5-flash | premium | excellent 12/12 | socks OK; lurex miss → need verify |",
        "| gemini-2.5-flash-lite | mid | excellent | lurex OK; socks→меланж miss |",
        "| gpt-4o-mini | mid-high | excellent | lurex miss; costlier |",
        "",
        "### Cheap bakeoff (this run)",
        "",
        "```json",
        json.dumps(compare, ensure_ascii=False, indent=2)[:4000],
        "```",
        "",
        "## Filter candidacy (LLM)",
        "",
    ]
    for d in decisions:
        lines.append(
            f"- **{d.get('name')}** → `{d.get('role')}` / {d.get('suggested_value_type')}: {d.get('why')}"
        )
    lines += [
        "",
        "## Schema (closed-set filters)",
        "",
    ]
    for a in schema.get("attributes") or []:
        lines.append(
            f"- `{a.get('attr_id')}` ({a.get('value_type')}): {', '.join(a.get('allowed_values') or [])}"
        )
        lines.append(f"  - why: {a.get('why_filter')}")
        lines.append(f"  - categories: {', '.join(a.get('categories') or [])}")

    lines += [
        "",
        "## Vision pilot results (unique pics → propagate)",
        "",
        "| attr | model | unique_pics | offers_after_propagate | coerced_rate | expected_match |",
        "|------|-------|-------------|------------------------|--------------|----------------|",
    ]
    for aid, s in vision.items():
        lines.append(
            f"| {aid} | {s.get('model')} | {s.get('n_unique_pics')} | {s.get('n_offers')} | "
            f"{s.get('coerced_rate')} | {s.get('expected_match_rate')} |"
        )

    demand = {}
    dem_path = OUT / "query_demand_evidence.json"
    if dem_path.is_file():
        demand = json.loads(dem_path.read_text(encoding="utf-8"))

    lines += [
        "",
        f"**Сделано хорошо (≥90% coerce):** {', '.join(done_attrs) or '—'}",
        f"**Слабо / не дожали:** {', '.join(weak_attrs) or '—'}",
        "",
        "## Demand evidence (ClickHouse) — источник правды по «имеет смысл»",
        "",
        "См. `FILTER_DEMAND_EVIDENCE.md` + `query_demand_evidence.json`.",
        "**Без этого файла вердикт «имеет смысл» = не пруф (только LLM/fashion).**",
        "",
    ]
    if demand:
        lines.append(
            f"siteId={demand.get('site_id')}, window={demand.get('window_days')}d, "
            f"top_n={demand.get('top_n')}, source=`{demand.get('source')}`"
        )
        lines.append("")
        lines.append("| attr | volume | share% | uniq | verdict |")
        lines.append("|------|--------|--------|------|---------|")
        for row in (demand.get("classification") or {}).get("intents") or []:
            lines.append(
                f"| `{row['attr_id']}` | {row['search_volume_in_top']} | "
                f"{row['share_of_top_pct']} | {row['uniq_queries']} | {row['verdict_hint']} |"
            )
        lines.append("")

    lines += [
        "## Text gold coerce (3826)",
        "",
        "```json",
        json.dumps(text_stats, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Backlog (только если CH strong / collision-checked)",
        "",
        f"- schema ids сейчас: {', '.join(schema_ids)}",
        "- `silhouette` — strong в CH, ещё не в vision pilot",
        "- `color` / `material` / `gender_target` — strong demand, но **feed/nav collision first**",
        "- `fit_waist` / `collar` / `pockets` — weak в топе; category-gated only",
        "",
        "## Dedupe rule",
        "",
        "Vision вызывается **1 раз на picture_url** (`picture_dedupe.normalize_picture_url`),",
        "затем значение размножается на все `offer_id` с той же картинкой.",
        "",
    ]
    path = OUT / "DETAILED_RESULTS.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("detailed →", path)
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--stage",
        default="all",
        choices=[
            "all",
            "samples",
            "candidacy",
            "schema",
            "vision",
            "compare_models",
            "text",
            "report",
        ],
    )
    ap.add_argument("--attrs", default=DEFAULT_ATTRS)
    ap.add_argument("--text-model", default=DEFAULT_TEXT_MODEL)
    ap.add_argument(
        "--vision-model",
        default="",
        help="Override vision model; empty = budget gemma-3-4b-it per attr",
    )
    ap.add_argument("--mode", default="discover", choices=["known", "discover"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    attrs = [a.strip() for a in args.attrs.split(",") if a.strip()]
    vision_override = (args.vision_model or "").strip() or None

    if args.stage in ("all", "samples"):
        stage_samples()
    if args.stage in ("all", "candidacy"):
        stage_candidacy(args.text_model)
    if args.stage in ("all", "schema"):
        stage_schema(args.text_model)
    if args.stage in ("all", "vision"):
        stage_vision(attrs, vision_override)
    if args.stage == "compare_models":
        stage_compare_models(attrs)
    if args.stage in ("all", "text"):
        stage_text()
    if args.stage in ("all", "report"):
        stage_report()
    print("DONE →", OUT)
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
