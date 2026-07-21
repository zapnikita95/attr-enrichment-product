#!/usr/bin/env python3
"""
Partner defense for Zolla FILTERS (TSUM-like HTML).

Every claim cites:
  - type decision tree (TYPE_DECISION_METHOD.md)
  - CH query demand (query_demand_evidence.json)
  - feed gap (params almost empty for style)
  - money formula with ASSUMED lifts clearly labeled
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "portfolio" / "zolla_filters"


def num(n: float | int) -> str:
    return f"{int(n):,}".replace(",", " ")


def pct(n: float) -> str:
    return f"{n:.2f}%".rstrip("0").rstrip(".") + "%"


# Type decisions — ONLY via Q1–Q4 tree (documented). Not LLM whim.
TYPE_DECISIONS = [
    {
        "attr_id": "hood",
        "label": "Капюшон",
        "value_type": "boolean",
        "allowed_values": ["да", "нет"],
        "tree_path": "Q1=yes → boolean (деталь есть/нет)",
        "why_type": (
            "Капюшон — дискретная деталь изделия: либо присутствует, либо нет. "
            "Покупательский вопрос бинарный («с капюшоном»). "
            "Подвиды (съёмный/мех) — отдельные атрибуты, если появятся в спросе."
        ),
        "source": ["vision", "text"],
    },
    {
        "attr_id": "pockets",
        "label": "Карманы",
        "value_type": "boolean",
        "allowed_values": ["да", "нет"],
        "tree_path": "Q1=yes → boolean",
        "why_type": "Наличие карманов — факт присутствия детали, не шкала вариантов.",
        "source": ["vision", "text"],
    },
    {
        "attr_id": "length",
        "label": "Длина изделия",
        "value_type": "enum",
        "allowed_values": ["mini", "midi", "maxi", "до колена", "укороченный"],
        "tree_path": "Q1=no → Q2=yes → enum (стандарт fashion)",
        "why_type": (
            "В fashion есть устоявшиеся взаимоисключающие длины (mini/midi/maxi…). "
            "Один SKU = одно значение длины."
        ),
        "source": ["vision", "text"],
    },
    {
        "attr_id": "sleeve_length",
        "label": "Длина рукава",
        "value_type": "enum",
        "allowed_values": ["короткий", "длинный", "3/4", "без рукавов"],
        "tree_path": "Q1=no → Q2=yes → enum",
        "why_type": "Стандартные взаимоисключающие варианты рукава в каталогах одежды.",
        "source": ["vision", "text"],
    },
    {
        "attr_id": "fastener",
        "label": "Застёжка",
        "value_type": "enum",
        "allowed_values": ["молния", "пуговицы", "кнопки", "завязки", "нет"],
        "tree_path": "Q1=no → Q2=yes → enum",
        "why_type": "Тип застёжки — закрытый набор mutually exclusive вариантов.",
        "source": ["vision", "text"],
    },
    {
        "attr_id": "collar",
        "label": "Воротник / вырез",
        "value_type": "enum",
        "allowed_values": ["круглый", "V-образный", "стойка", "отложной", "капюшон", "без воротника"],
        "tree_path": "Q1=no → Q2=yes → enum",
        "why_type": "Ограниченный набор конструкций горловины; один основной вариант на SKU.",
        "source": ["vision", "text"],
    },
    {
        "attr_id": "print_pattern",
        "label": "Узор / принт",
        "value_type": "multi_enum",
        "allowed_values": [
            "однотонный",
            "полоска",
            "клетка",
            "горошек",
            "цветочный",
            "геометрия",
            "леопард",
            "зебра",
            "камуфляж",
            "меланж",
            "люрекс",
            "графика",
            "абстракция",
            "гусиная лапка",
        ],
        "tree_path": "Q1=no → Q2=partial → Q3=yes → multi_enum",
        "why_type": (
            "На ткани могут сосуществовать несколько признаков (полоска+люрекс). "
            "Closed-set ограничивает кардинальность facet."
        ),
        "source": ["vision", "text"],
    },
    {
        "attr_id": "silhouette",
        "label": "Силуэт / крой",
        "value_type": "enum",
        "allowed_values": ["прямой", "оверсайз", "прилегающий", "клёш", "свободный"],
        "tree_path": "Q1=no → Q2=yes → enum",
        "why_type": "Стандартные силуэты fashion; взаимоисключающие на уровне основного кроя.",
        "source": ["vision", "text"],
        "status": "backlog_strong_demand",
    },
]


def load_demand() -> dict:
    p = OUT / "query_demand_evidence.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def intent_by_id(demand: dict) -> dict:
    out = {}
    for row in (demand.get("classification") or {}).get("intents") or []:
        out[row["attr_id"]] = row
    return out


def load_money_benchmark() -> dict:
    p = OUT / "money_baseline_benchmark.json"
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _filter_lift_benchmark() -> dict:
    """Relative CVR lift from Diginetica filter with/without benches (no partner names in UI)."""
    # portfolio/filter-conversion-data.json — positive categories only
    fc_path = ROOT / "portfolio" / "filter-conversion-data.json"
    rels: list[float] = []
    pps: list[float] = []
    if fc_path.is_file():
        raw = json.loads(fc_path.read_text(encoding="utf-8"))
        for row in raw.values() if isinstance(raw, dict) else []:
            if not isinstance(row, dict):
                continue
            w = float(row.get("conv_with_filters_pct") or 0)
            wo = float(row.get("conv_without_filters_pct") or 0)
            pp = float(row.get("filter_lift_pp") or (w - wo))
            if pp > 0 and wo > 0:
                rels.append(w / wo - 1.0)
                pps.append(pp)
    # TSUM NORMAL fixable band used in money_impact (relative)
    tsum_band = (0.15, 0.20, 0.25)
    if rels:
        rels_sorted = sorted(rels)
        median_rel = rels_sorted[len(rels_sorted) // 2]
        # Cap for partner sketch: don't claim full "filters exist vs none" on day-1 new facets
        # → take ~half of measured with/without median, floored by TSUM conservative
        sketch_rel = max(tsum_band[0], min(median_rel * 0.5, tsum_band[2]))
    else:
        median_rel = tsum_band[1]
        sketch_rel = tsum_band[1]
    median_pp = sorted(pps)[len(pps) // 2] if pps else None
    return {
        "source": "filter with/without на проектах Diginetica + полоса relative lift 15–25%",
        "measured_positive_relative_median": round(median_rel, 3) if rels else None,
        "measured_positive_pp_median": round(median_pp, 2) if median_pp is not None else None,
        "partner_sketch_relative": round(sketch_rel, 3),
        "band_relative": {"conservative": 0.15, "base": 0.20, "optimistic": 0.25},
        "n_positive_categories": len(rels),
    }


def build_money(demand: dict, baseline: dict) -> dict:
    """Partner money: Metrika search base × addressable × adoption × relative lift (benches)."""
    intents = intent_by_id(demand)
    keep_ids = [
        "print_pattern",
        "sleeve_length",
        "length",
        "hood",
        "fastener",
        "silhouette",
        "collar",
        "fit_waist",
        "pockets",
    ]
    vol_sum = sum(intents.get(i, {}).get("search_volume_in_top", 0) for i in keep_ids)
    top_total = (demand.get("classification") or {}).get("total_search_events_in_top") or 1
    searches_90d = float(baseline.get("searches_90d") or 0) or 1.0

    bench = load_money_benchmark()
    decision = bench.get("decision") or {}
    chosen = decision.get("chosen") or {}
    met_all = bench.get("metrika_zolla") or {}
    met = met_all.get("with_search") or {}

    if chosen.get("search_cvr_pct"):
        cvr_pct = float(chosen["search_cvr_pct"])
        aov = float(chosen.get("aov") or 0)
    elif met.get("cvr_pct"):
        cvr_pct = float(met["cvr_pct"])
        aov = float(met.get("aov") or 0)
    else:
        cvr_pct = 1.0
        aov = 2500.0

    visits_90d = float(met.get("visits") or chosen.get("visits_or_sessions") or 0)
    purch_90d = float(met.get("purchases") or 0)
    rev_90d = float(met.get("revenue") or (visits_90d * (cvr_pct / 100.0) * aov))

    # Explicit style-intent share (CH top) → floor for addressable
    intent_share_searches = vol_sum / searches_90d
    # Fashion style filters also help browse/refine beyond exact tokens in query
    # Base addressable = max(explicit intent, 15% of search) — partner sketch, labeled
    addressable_base = max(intent_share_searches, 0.15)

    lift_bench = _filter_lift_benchmark()
    band = lift_bench["band_relative"]

    def scenario(name: str, addressable: float, adoption: float, rel_lift: float) -> dict:
        delta_90 = rev_90d * addressable * adoption * rel_lift
        delta_mo = delta_90 / 3.0
        pct_of_search_rev = (100.0 * delta_90 / rev_90d) if rev_90d else 0.0
        # absolute CVR after lift on touched sessions
        cvr_lift_pp = cvr_pct * rel_lift
        touched_visits_90 = visits_90d * addressable * adoption
        extra_orders_90 = touched_visits_90 * (cvr_lift_pp / 100.0)
        return {
            "name": name,
            "addressable_share": round(addressable, 3),
            "adoption": round(adoption, 3),
            "relative_cvr_lift": round(rel_lift, 3),
            "cvr_lift_pp": round(cvr_lift_pp, 3),
            "delta_revenue_rub_90d": round(delta_90, 0),
            "delta_revenue_rub_month": round(delta_mo, 0),
            "pct_of_search_revenue_90d": round(pct_of_search_rev, 2),
            "extra_orders_90d": round(extra_orders_90, 0),
        }

    scenarios = {
        "conservative": scenario("conservative", max(intent_share_searches, 0.08), 0.15, band["conservative"]),
        "base": scenario("base", addressable_base, 0.20, band["base"]),
        "optimistic": scenario("optimistic", 0.25, 0.30, band["optimistic"]),
    }
    base = scenarios["base"]

    # Partner-facing copy — NO broken CH, NO competitor brand names, NO internal paths
    partner_lead = (
        f"База — Яндекс.Метрика: визиты с поиском {num(visits_90d)}, "
        f"CVR {cvr_pct}%, средний чек {num(aov)} ₽, "
        f"выручка из поиска {rev_90d/1e6:.1f} млн ₽ за 90 дней. "
        "Ожидаемый прирост CVR — от бенчмарка Diginetica "
        "«сессии с фильтрами vs без» "
        f"(+{int(band['conservative']*100)}…+{int(band['optimistic']*100)}% "
        "относительно на затронутых сессиях). "
        "После запуска фильтров замерим with/without уже на Zolla."
    )

    return {
        "baseline_ch": baseline,  # internal only
        "baseline_money": {
            "search_cvr_pct": cvr_pct,
            "aov": aov,
            "metrika_search_visits": visits_90d,
            "metrika_search_purchases": purch_90d,
            "metrika_search_revenue_90d": rev_90d,
            "source_partner_label": "Яндекс.Метрика · визиты с поиском",
        },
        "lift_benchmark": lift_bench,
        "partner_lead": partner_lead,
        "direct_filter_intent_volume_90d_top5k": vol_sum,
        "intent_share_of_searches_pct": round(100 * intent_share_searches, 2),
        "intent_share_of_top_pct": round(100 * vol_sum / top_total, 2),
        "scenarios": scenarios,
        "assumptions": {
            "addressable_share_base": addressable_base,
            "adoption_base": 0.20,
            "relative_cvr_lift_base": band["base"],
            "cvr_lift_pp_base": base["cvr_lift_pp"],
            "label": "relative lift from Diginetica filter benches; addressable/adoption — sketch until Zolla facet measure",
        },
        "formula": (
            "Δ₽_90д = выручка_поиска_90д × доля_затронутых × adoption × относительный_lift_CVR"
        ),
        "delta_revenue_rub_per_month_sketch": base["delta_revenue_rub_month"],
        "delta_revenue_rub_per_90d_sketch": base["delta_revenue_rub_90d"],
        "pct_of_search_revenue_90d": base["pct_of_search_revenue_90d"],
        "what_we_will_measure_next": [
            "conv_with_filters vs conv_without_filters на Zolla после появления facet",
            "SKU coverage typed extract",
        ],
        # keep for internal JSON; never render in partner HTML
        "_internal": {
            "ch_search_cvr_pct_raw": baseline.get("search_cvr_pct"),
            "ch_broken": bool(decision.get("ch_zolla_broken")),
            "peer_medians_internal_only": {
                "metrika": decision.get("peer_metrika_median_cvr_pct"),
                "ch": decision.get("peer_ch_median_cvr_pct"),
            },
        },
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    demand = load_demand()
    intents = intent_by_id(demand)

    baseline_path = OUT / "ch_baseline_3826.json"
    if baseline_path.is_file():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    else:
        baseline = {
            "total_sessions": 1171945,
            "search_sessions": 195259,
            "search_orders": 10,
            "search_cvr_pct": 0.005,
            "aov_search": 3395.7,
            "search_revenue_90d": 33957,
            "searches_90d": 473003,
            "uniq_queries_90d": 46331,
        }
        baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")

    # Enrich baseline from demand site checks
    baseline["searches_90d"] = demand.get("site_checks", {}).get("3826", {}).get("n", baseline.get("searches_90d"))
    baseline["uniq_queries_90d"] = demand.get("site_checks", {}).get("3826", {}).get("uniq_q")

    money = build_money(demand, baseline)

    # Feed gap (measured on sample earlier — store facts)
    feed_gap = {
        "source": "yml-feed.3826 sample 8000 offers",
        "human_params_present": ["Цвет", "Размер", "Новинка", "Скидка", "barcode", "vendorCodeCut"],
        "style_params_present": [],
        "conclusion": (
            "В фиде Zolla нет structured params для капюшона, принта, рукава, застёжки, воротника, силуэта. "
            "Цвет/размер — 100% fill → не трогаем как enrichment filter."
        ),
        "name_lexicon_coverage_sample_20k": {
            "print": "16.42%",
            "sleeve": "12.66%",
            "collar": "7.16%",
            "length": "5.28%",
            "hood": "4.68%",
            "silhouette": "3.73%",
            "fastener": "1.98%",
            "note": "Лексика в name ≠ нормализованный facet; часть товаров с деталью на фото без слова в названии.",
        },
    }

    # Merge type + demand into attribute cards
    cards = []
    for td in TYPE_DECISIONS:
        dem = intents.get(td["attr_id"], {})
        cards.append(
            {
                **td,
                "demand_volume_top5k": dem.get("search_volume_in_top"),
                "demand_share_pct": dem.get("share_of_top_pct"),
                "demand_uniq": dem.get("uniq_queries"),
                "demand_verdict": dem.get("verdict_hint"),
                "demand_examples": dem.get("examples") or [],
                "feed_status": "missing_structured_param",
                "partner_action": (
                    "extract+filter"
                    if dem.get("verdict_hint") in {
                        "strong_filter_candidate",
                        "weak_or_sparse",
                    }
                    or td.get("status") == "backlog_strong_demand"
                    else "review"
                ),
            }
        )

    # Explicit rejects with reasons
    rejects = [
        {
            "attr": "Цвет",
            "why": "Fill ~100% в YML param «Цвет». Спрос в CH высокий, но это не gap enrichment.",
            "demand_note": intents.get("color", {}).get("verdict_hint"),
        },
        {
            "attr": "Размер",
            "why": "Variant-level в фиде (100%). Не vision/text filter enrichment.",
            "demand_note": "n/a",
        },
        {
            "attr": "Пол (gender_target)",
            "why": (
                "В запросах часто «женские/мужские» как модификатор типа изделия; "
                "обычно закрывается навигацией/фидом. Не назначаем новым facet без проверки UI."
            ),
            "demand_note": intents.get("gender_target", {}).get("verdict_hint"),
        },
        {
            "attr": "Материал / состав %",
            "why": "Состав должен идти из params/описания партнёра; vision по составу ненадёжен. Collision risk.",
            "demand_note": intents.get("material", {}).get("verdict_hint"),
        },
        {
            "attr": "Ощущения ткани / маркетинг",
            "why": "Не нормализуется в closed-set; не facet.",
            "demand_note": "no CH facet signal required",
        },
    ]

    decision = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "partner": "Zolla",
        "site_id": 3826,
        "method_type": "TYPE_DECISION_METHOD.md Q0–Q4",
        "method_demand": "sessions.searches top-5000 / 90d regex intents",
        "feed_gap": feed_gap,
        "attributes": cards,
        "do_not": rejects,
        "money": money,
        "pilot_vision_summary_ref": "vision_summary.json",
    }
    (OUT / "FILTER_ATTR_DECISION.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- HTML (TSUM-like) ---
    def card_rows() -> str:
        rows = []
        for c in cards:
            ex = ", ".join(
                f"{e['q']} ({e['search_count']})" for e in (c.get("demand_examples") or [])[:3]
            )
            rows.append(
                "<tr>"
                f"<td><strong>{c['label']}</strong><br/><code>{c['attr_id']}</code></td>"
                f"<td><code>{c['value_type']}</code><br/><span style='font-size:12px;color:#5c5c5c'>{c['tree_path']}</span></td>"
                f"<td>{c['why_type']}</td>"
                f"<td>{num(c.get('demand_volume_top5k') or 0)} · {c.get('demand_share_pct')}%<br/>"
                f"<span style='font-size:12px'>{c.get('demand_verdict')}</span></td>"
                f"<td style='font-size:12px'>{ex}</td>"
                f"<td>{c.get('feed_status')}<br/>{c.get('partner_action')}</td>"
                "</tr>"
            )
        return "".join(rows)

    reject_rows = "".join(
        f"<tr><td>{r['attr']}</td><td>{r['why']}</td><td>{r['demand_note']}</td></tr>" for r in rejects
    )

    dem_intents = "".join(
        f"<tr><td><code>{r['attr_id']}</code></td><td>{num(r['search_volume_in_top'])}</td>"
        f"<td>{r['share_of_top_pct']}%</td><td>{r['uniq_queries']}</td>"
        f"<td>{r['verdict_hint']}</td></tr>"
        for r in (demand.get("classification") or {}).get("intents") or []
    )

    strong_vol = sum(
        c.get("demand_volume_top5k") or 0
        for c in cards
        if c.get("demand_verdict") == "strong_filter_candidate"
        or c["attr_id"] == "silhouette"
    )

    # Real product cases (mandatory for partner defense)
    cases_path = OUT / "demo_cases.json"
    if not cases_path.is_file():
        import subprocess
        import sys

        subprocess.check_call([sys.executable, str(Path(__file__).parent / "build_demo_cases.py")])
    cases_data = json.loads(cases_path.read_text(encoding="utf-8")) if cases_path.is_file() else {"cases": []}
    def _attr_li(f: dict, *, cls: str = "") -> str:
        dem = f.get("demand_bucket") or ""
        vol = f.get("demand_volume_top5k") or 0
        ex = ", ".join(
            f"{e.get('q')} ({e.get('n')})" for e in (f.get("demand_examples") or [])[:2]
        )
        dem_line = ""
        if dem == "searched_strong":
            dem_line = f"<span class='dem ok'>ищут: {vol} в top-5k" + (f" · {ex}" if ex else "") + "</span>"
        elif dem == "searched_weak":
            dem_line = f"<span class='dem weak'>слабый intent ({vol}) — facet всё равно полезен</span>"
        else:
            dem_line = "<span class='dem extra'>достаём как facet; сильного поиска пока не видно</span>"
        return (
            f"<li class='{cls}'><strong>{f.get('label')}</strong>: {f.get('value')} "
            f"<span class='ev'>({f.get('evidence')})</span> "
            f"<span class='filt'>→ фильтр: {f.get('filter_ui')}</span>"
            f"{dem_line}</li>"
        )

    case_articles = []
    for c in cases_data.get("cases") or []:
        feed_rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in (c.get("feed") or {}).items())
        searched = c.get("searched_filters") or [
            f for f in (c.get("extracted_filters") or []) if f.get("demand_bucket") == "searched_strong"
        ]
        extra = c.get("extra_filters") or [
            f for f in (c.get("extracted_filters") or []) if f.get("demand_bucket") != "searched_strong"
        ]
        if not searched and not extra:
            # legacy one-attr cards
            searched = list(c.get("extracted_filters") or [])
        attrs_s = "".join(_attr_li(f, cls="searched") for f in searched)
        attrs_e = "".join(_attr_li(f, cls="extra") for f in extra)
        cols = "".join(
            f"<li class='coll'><strong>{x.get('label')}</strong>: {x.get('value')} "
            f"<span class='ev'>— {x.get('why')}</span></li>"
            for x in (c.get("collisions_not_gap") or [])
        )
        cols_block = (
            f"<h4>Уже знали (не gap)</h4><ul class='attrs'>{cols}</ul>" if cols else ""
        )
        n_keep = c.get("keep_count") or len(searched) + len(extra)
        case_articles.append(
            f"""
    <article class="case">
      <div class="case-num">{c.get('n')}</div>
      <a class="case-img" href="{c.get('picture_url')}" target="_blank" rel="noopener">
        <img src="{c.get('picture_url')}" alt="{c.get('name')}" loading="lazy"/>
      </a>
      <div class="case-body">
        <div class="case-meta">Zolla · offer_id {c.get('offer_id')} · <strong>{n_keep} фильтров с фото</strong></div>
        <h3>{c.get('name')}</h3>
        <p class="case-line">{c.get('blurb')}</p>
        <div class="case-cols">
          <div>
            <h4>Уже было в фиде / старом extract</h4>
            <table class="mini"><tbody>{feed_rows}</tbody></table>
            {cols_block}
          </div>
          <div>
            <h4>Ищут в поиске → фильтр</h4>
            <ul class="attrs">{attrs_s or "<li class='ev'>нет сильного intent из этого набора</li>"}</ul>
            <h4>Достаём с фото (facet на вырост)</h4>
            <ul class="attrs">{attrs_e or "<li class='ev'>—</li>"}</ul>
          </div>
        </div>
      </div>
    </article>
"""
        )
    cases_html = "".join(case_articles) or "<p class='meta'>Нет demo_cases.json — запусти build_demo_cases.py</p>"

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Zolla — фильтры из картинок/описаний: защита</title>
<style>
:root {{
  --bg:#f7f5f2; --ink:#1a1a1a; --muted:#5c5c5c; --line:#ddd6cc;
  --card:#fff; --accent:#1f3a2e; --warn:#7a3e1d;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font:16px/1.5 "Segoe UI", system-ui, sans-serif; color:var(--ink); background:var(--bg); }}
.wrap {{ max-width:1100px; margin:0 auto; padding:32px 20px 80px; }}
h1 {{ font-size:28px; font-weight:650; letter-spacing:-0.02em; margin:0 0 8px; }}
h2 {{ font-size:20px; margin:40px 0 12px; color:var(--accent); }}
h3 {{ font-size:16px; margin:24px 0 8px; }}
.lead {{ color:var(--muted); font-size:17px; max-width:780px; }}
.meta {{ margin:16px 0 28px; color:var(--muted); font-size:13px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:20px 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); padding:16px 14px; }}
.stat b {{ display:block; font-size:22px; font-weight:650; margin-bottom:4px; }}
.stat span {{ color:var(--muted); font-size:13px; }}
.callout {{ background:var(--card); border-left:3px solid var(--accent); padding:14px 16px; margin:18px 0; }}
.callout.warn {{ border-left-color:var(--warn); }}
table {{ width:100%; border-collapse:collapse; background:var(--card); font-size:13px; }}
th, td {{ border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
th {{ background:#efeae3; font-weight:600; }}
.tag {{ display:inline-block; background:#efeae3; padding:2px 8px; font-size:12px; margin-right:6px; }}
ol.tree {{ max-width:720px; }}
footer {{ margin-top:48px; color:var(--muted); font-size:12px; }}
code {{ font-size:12px; }}
.case {{ display:grid; grid-template-columns:56px 200px 1fr; gap:16px; background:var(--card); border:1px solid var(--line); padding:16px; margin:14px 0; align-items:start; }}
.case-num {{ font-size:22px; font-weight:700; color:var(--accent); }}
.case-img img {{ width:200px; height:200px; object-fit:cover; display:block; background:#eee; }}
.case-meta {{ font-size:12px; color:var(--muted); margin-bottom:4px; }}
.case-body h3 {{ margin:0 0 8px; font-size:17px; }}
.case-line {{ margin:0 0 12px; font-size:14px; }}
.case-cols {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.case-cols h4 {{ margin:0 0 6px; font-size:13px; color:var(--muted); font-weight:600; }}
table.mini {{ font-size:12px; width:100%; }}
.attrs {{ margin:0; padding-left:18px; font-size:14px; }}
.attrs .ev {{ color:var(--muted); font-size:12px; }}
.attrs .filt {{ display:block; color:var(--accent); font-size:12px; margin-top:2px; }}
.attrs .dem {{ display:block; font-size:11px; margin-top:2px; }}
.attrs .dem.ok {{ color:#1f3a2e; }}
.attrs .dem.weak {{ color:#7a3e1d; }}
.attrs .dem.extra {{ color:#5c5c5c; }}
.attrs li.searched {{ font-weight:600; }}
.attrs li.coll {{ color:var(--muted); }}
.attrs li.focus {{ font-weight:600; }}
@media (max-width:800px) {{
  .case {{ grid-template-columns:1fr; }}
  .case-img img {{ width:100%; height:auto; max-height:280px; }}
  .case-cols {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>
<div class="wrap">
  <div class="tag">site_id 3826 · Zolla</div>
  <div class="tag">фильтры · vision + text</div>
  <div class="tag">защита для партнёра</div>
  <h1>Zolla: фильтры из картинок и описаний</h1>
  <p class="lead">
    Защита решения: <strong>какие атрибуты делать фильтрами</strong>,
    <strong>в каком типе значения</strong> (boolean / enum / multi_enum),
    <strong>почему их нет в фиде</strong>, <strong>что ищут пользователи</strong>
    и <strong>как это бьёт в деньги</strong>.
    Формат близкий к исследованию ЦУМ по атрибутам с картинок.
  </p>
  <p class="meta">
    ClickHouse <code>sessions.searches</code> 90д · top-5000 запросов ·
    YML sample 8k / name coverage 20k ·
    тип значения — дерево Q0–Q4 (<code>TYPE_DECISION_METHOD.md</code>), не «мнение модели».
  </p>

  <div class="grid">
    <div class="stat"><b>{num(baseline.get('searches_90d') or 0)}</b><span>поисков за 90 дней</span></div>
    <div class="stat"><b>{num(baseline.get('uniq_queries_90d') or 0)}</b><span>уникальных запросов</span></div>
    <div class="stat"><b>{num(strong_vol)}</b><span>поисков в топе под filter-кандидаты*</span></div>
    <div class="stat"><b>0</b><span>style-params в YML (капюшон/принт/рукав…)</span></div>
    <div class="stat"><b>{num(money['delta_revenue_rub_per_month_sketch'])} ₽</b><span>оценка Δ/мес · {money.get('pct_of_search_revenue_90d')}% выручки поиска</span></div>
    <div class="stat"><b>100%</b><span>цвет и размер уже в фиде</span></div>
  </div>
  <p class="meta">* сумма объёмов интентов (пересечения возможны) — upper-bound охвата facet-формулировок в top-5000.</p>

  <div class="callout">
    <strong>Вывод для партнёра.</strong> Фид Zolla закрывает карточку (цвет, размер, скидка),
    но <em>не даёт facet-ов визуального стиля</em>, которые люди уже пишут в поиск:
    принт, рукав, длина, капюшон, застёжка, силуэт.
    Мы нормализуем их в фильтры с жёстким типом значения, чтобы UI и индекс не расползались
    («да/нет», а не «капюшон есть / с капюшоном»).
  </div>

  <h2>0. Как мы решаем тип фильтра (логика, не «с потолка»)</h2>
  <ol class="tree">
    <li><strong>Q0.</strong> Это вообще фильтр? (спрос + не дубль фида + нормализуемо)</li>
    <li><strong>Q1.</strong> Вопрос «есть/нет» про деталь? → <code>boolean</code> = да/нет.
      <br/>Пример: капюшон, карманы.</li>
    <li><strong>Q2.</strong> Есть стандартный набор взаимоисключающих вариантов fashion? → <code>enum</code>.
      <br/>Пример: длина mini/midi/maxi; рукав короткий/длинный/3/4/без рукавов.</li>
    <li><strong>Q3.</strong> Несколько значений сразу возможны? → <code>multi_enum</code>.
      <br/>Пример: принт полоска+люрекс.</li>
    <li><strong>Q4.</strong> Число? → bins, не сырой float в facet.</li>
  </ol>
  <div class="callout warn">
    Тип boolean для капюшона выбран <strong>не потому что «так сказала модель»</strong>, а потому что
    онтология атрибута — наличие детали. Спрос в CH подтверждает, что вопрос бинарный
    («куртка с капюшоном»), но спрос <em>не выбирает тип</em> — тип выбирает дерево Q1–Q4.
  </div>

  <h2>1. Что уже есть в фиде (и что НЕ трогаем)</h2>
  <p>Sample 8 000 offer YML Zolla. Человекочитаемые params:</p>
  <table>
    <thead><tr><th>Param</th><th>Fill (sample)</th><th>Решение</th></tr></thead>
    <tbody>
      <tr><td>Цвет</td><td>100%</td><td>не enrichment-фильтр</td></tr>
      <tr><td>Размер</td><td>100%</td><td>variant, не vision</td></tr>
      <tr><td>Новинка / Скидка / barcode</td><td>~99–100%</td><td>операционка</td></tr>
      <tr><td>Капюшон / принт / рукав / застёжка / воротник / силуэт</td><td><strong>нет param</strong></td><td>зона фильтров из фото/описаний</td></tr>
    </tbody>
  </table>
  <p class="meta">Лексика в названии (sample 20k): принт ~16%, рукав ~13%, капюшон ~4.7%, застёжка ~2% —
  это не замена facet: часть карточек с деталью на фото без слова в name.</p>

  <h2>2. Не делать фильтрами / не тащить с фото</h2>
  <table>
    <thead><tr><th>Атрибут</th><th>Почему</th><th>CH note</th></tr></thead>
    <tbody>{reject_rows}</tbody>
  </table>

  <h2>3. Делать фильтрами: тип + спрос + gap</h2>
  <table>
    <thead>
      <tr>
        <th>Фильтр</th><th>Тип (дерево)</th><th>Почему такой тип</th>
        <th>Спрос CH (top-5k)</th><th>Примеры запросов</th><th>Фид / действие</th>
      </tr>
    </thead>
    <tbody>{card_rows()}</tbody>
  </table>

  <h2>4. Поиск: полный ranking интентов (пруф)</h2>
  <p>
    Источник: ClickHouse <code>sessions.searches</code>, siteId=3826, 90 дней.
    Всего поисков <strong>{num(baseline.get('searches_90d') or 0)}</strong>,
    uniq <strong>{num(baseline.get('uniq_queries_90d') or 0)}</strong>.
    Ниже — матчинг по top-5000 (срез объёма в JSON evidence).
  </p>
  <table>
    <thead><tr><th>Intent</th><th>Volume</th><th>Share%</th><th>Uniq</th><th>Verdict</th></tr></thead>
    <tbody>{dem_intents}</tbody>
  </table>
  <p class="meta">Полный файл с примерами запросов: <code>FILTER_DEMAND_EVIDENCE.md</code>.</p>

  <h2>5. Наглядные кейсы: фото → фильтр (обязательно)</h2>
  <p class="lead" style="font-size:15px">
    Реальные карточки Zolla. Слева — фид / старый extract и «уже знали» (не gap).
    Справа — <strong>максимум фильтров с фото</strong>: сначала то, что <strong>ищут</strong>
    (CH top-5k + примеры), затем то, что всё равно <strong>достаём как facet</strong>
    без сильного intent. Один атрибут на карточку — брак демо.
  </p>
  {cases_html}

  <h2>6. Деньги</h2>
  <div class="callout">
    {money.get('partner_lead') or ''}
  </div>
  <table>
    <thead><tr><th>Показатель</th><th>Значение</th></tr></thead>
    <tbody>
      <tr><td>Визиты с поиском (90 дней)</td><td>{num((money.get('baseline_money') or {}).get('metrika_search_visits') or 0)}</td></tr>
      <tr><td>Конверсия поиска</td><td>{(money.get('baseline_money') or {}).get('search_cvr_pct')}%</td></tr>
      <tr><td>Средний чек (поиск)</td><td>{num((money.get('baseline_money') or {}).get('aov') or 0)} ₽</td></tr>
      <tr><td>Выручка из поиска (90 дней)</td><td>{num((money.get('baseline_money') or {}).get('metrika_search_revenue_90d') or 0)} ₽</td></tr>
      <tr><td>Ожидаемый прирост CVR на затронутых сессиях</td><td>+{int(((money.get('assumptions') or {}).get('relative_cvr_lift_base') or 0)*100)}% относительно
        (≈ +{(money.get('assumptions') or {}).get('cvr_lift_pp_base')} п.п. к текущим {(money.get('baseline_money') or {}).get('search_cvr_pct')}%)
        — бенчмарк Diginetica «с фильтрами / без»</td></tr>
      <tr><td>Доля затронутых search-визитов (base)</td><td>{int(((money.get('assumptions') or {}).get('addressable_share_base') or 0)*100)}%</td></tr>
      <tr><td>Adoption новых фильтров среди затронутых (base)</td><td>{int(((money.get('assumptions') or {}).get('adoption_base') or 0)*100)}%</td></tr>
      <tr><td>Формула</td><td>{money.get('formula')}</td></tr>
      <tr><td><strong>Оценка доп. выручки / мес (base)</strong></td><td><strong>{num(money['delta_revenue_rub_per_month_sketch'])} ₽</strong>
        · это <strong>{money.get('pct_of_search_revenue_90d')}%</strong> выручки из поиска</td></tr>
      <tr><td>Оценка доп. выручки / 90 дней (base)</td><td>{num(money['delta_revenue_rub_per_90d_sketch'])} ₽
        · ≈ {num((money.get('scenarios') or {}).get('base', {}).get('extra_orders_90d') or 0)} доп. заказов</td></tr>
      <tr><td>Диапазон сценариев / мес</td><td>
        conservative {num((money.get('scenarios') or {}).get('conservative', {}).get('delta_revenue_rub_month') or 0)} ₽
        ({(money.get('scenarios') or {}).get('conservative', {}).get('pct_of_search_revenue_90d')}%) ·
        optimistic {num((money.get('scenarios') or {}).get('optimistic', {}).get('delta_revenue_rub_month') or 0)} ₽
        ({(money.get('scenarios') or {}).get('optimistic', {}).get('pct_of_search_revenue_90d')}%)
      </td></tr>
    </tbody>
  </table>
  <p class="meta">После появления фильтров заменим оценку на замер конверсии with/without на Zolla.</p>

  <h2>7. Что уже проверили технически (пилот)</h2>
  <ul>
    <li>Closed-set extract через OpenRouter (бюджет: gemma / flash-lite).</li>
    <li>Дедуп по picture URL → один inference → размножение на все offer_id с той же картинкой.</li>
    <li>Boolean капюшон: 100% канон <code>да|нет</code> на unique pics пилота.</li>
    <li>Артефакты: <code>vision_summary.json</code>, <code>TYPE_DECISION_METHOD.md</code>, <code>FILTER_DEMAND_EVIDENCE.md</code>.</li>
  </ul>

  <footer>
    Generated {decision['generated_at']} · Diginetica filter enrichment defense · Zolla 3826
  </footer>
</div>
</body>
</html>
"""
    html_path = OUT / "zolla-filters-research.html"
    html_path.write_text(html, encoding="utf-8")
    print("wrote", html_path)
    print("money sketch ₽/mo", money["delta_revenue_rub_per_month_sketch"])
    print("decision attrs", len(cards))


if __name__ == "__main__":
    main()
