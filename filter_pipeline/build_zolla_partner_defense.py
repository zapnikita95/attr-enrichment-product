#!/usr/bin/env python3
"""
Partner-facing research HTML for Zolla filters (photo + description).

Internal JSON keeps full proofs; HTML must be shareable with the partner:
no other brands, no internal CH/LLM jargon, human Russian.
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
        "source": "бенчмарк сессий с фильтрами vs без + полоса relative lift 15–25%",
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
        f"База — Яндекс.Метрика Zolla: визиты с поиском {num(visits_90d)}, "
        f"конверсия {cvr_pct}%, средний чек {num(aov)} ₽, "
        f"выручка из поиска {rev_90d/1e6:.1f} млн ₽ за 90 дней. "
        "Ожидаемый прирост конверсии — от бенчмарка "
        "«сессии с фильтрами vs без» "
        f"(+{int(band['conservative']*100)}…+{int(band['optimistic']*100)}% "
        "относительно на затронутых сессиях). "
        "После запуска фильтров замерим эффект уже на ваших данных."
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
            "label": "relative lift from filter with/without benches; sketch until Zolla facet measure",
        },
        "formula": (
            "Доп. выручка за 90 дней = выручка из поиска × доля затронутых визитов "
            "× доля пользователей фильтров × относительный прирост конверсии"
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

    # Explicit rejects with reasons (partner-facing wording)
    rejects = [
        {
            "attr": "Цвет",
            "why": "Уже заполнен в фиде (~100%). Спрос в поиске высокий, но это не новый gap.",
            "demand_note": intents.get("color", {}).get("verdict_hint"),
        },
        {
            "attr": "Размер",
            "why": "Уже есть в вариантах товара (100%). Не извлекаем с фото.",
            "demand_note": "n/a",
        },
        {
            "attr": "Пол",
            "why": (
                "В запросах часто «женские / мужские» как уточнение типа изделия; "
                "обычно уже закрыто навигацией и фидом."
            ),
            "demand_note": intents.get("gender_target", {}).get("verdict_hint"),
        },
        {
            "attr": "Материал / состав %",
            "why": "Состав надёжнее брать из параметров и описания; с фото проценты состава ненадёжны.",
            "demand_note": intents.get("material", {}).get("verdict_hint"),
        },
        {
            "attr": "Ощущения ткани / маркетинг",
            "why": "Не сводится к фиксированному списку значений — плохой фильтр.",
            "demand_note": "n/a",
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

    # --- Partner-facing HTML (no other brands, no internal jargon) ---
    VERDICT_RU = {
        "strong_filter_candidate": "сильный кандидат в фильтр",
        "weak_or_sparse": "слабый / редкий спрос",
        "strong_demand_but_check_feed_nav_collision": "спрос есть, уже закрыто фидом/навигацией",
        "proxy_product_type_not_facet": "скорее тип товара, не отдельный фильтр",
    }
    INTENT_LABEL_RU = {
        "gender_target": "Пол",
        "color": "Цвет",
        "material": "Материал",
        "sleeve_length_product_proxy": "Короткий рукав (как тип изделия)",
        "print_pattern": "Узор / принт",
        "sleeve_length": "Длина рукава",
        "length": "Длина изделия",
        "hood": "Капюшон",
        "fastener": "Застёжка",
        "silhouette": "Силуэт / крой",
        "collar": "Воротник / вырез",
        "fit_waist": "Пояс / талия",
        "pockets": "Карманы",
    }
    FEED_STATUS_RU = {
        "missing_structured_param": "нет в фиде как фильтр",
        "extract+filter": "достаём и делаем фильтром",
    }
    TYPE_RU = {
        "boolean": "да / нет",
        "enum": "один из списка",
        "multi_enum": "несколько из списка",
    }

    def _verdict_ru(v: str) -> str:
        return VERDICT_RU.get(v or "", "на рассмотрении")

    def card_rows() -> str:
        rows = []
        for c in cards:
            ex = ", ".join(
                f"{e['q']} ({e['search_count']})" for e in (c.get("demand_examples") or [])[:3]
            )
            action = FEED_STATUS_RU.get(c.get("partner_action") or "", "в работу")
            feed = FEED_STATUS_RU.get(c.get("feed_status") or "", "нет в фиде как фильтр")
            rows.append(
                "<tr>"
                f"<td><strong>{c['label']}</strong></td>"
                f"<td>{TYPE_RU.get(c['value_type'], c['value_type'])}</td>"
                f"<td>{c['why_type']}</td>"
                f"<td>{num(c.get('demand_volume_top5k') or 0)} "
                f"({c.get('demand_share_pct')}%)<br/>"
                f"<span style='font-size:12px;color:#5c5c5c'>{_verdict_ru(c.get('demand_verdict') or '')}</span></td>"
                f"<td style='font-size:12px'>{ex}</td>"
                f"<td>{feed}<br/>{action}</td>"
                "</tr>"
            )
        return "".join(rows)

    reject_rows = "".join(
        f"<tr><td>{r['attr']}</td><td>{r['why']}</td></tr>" for r in rejects
    )

    dem_intents = "".join(
        "<tr>"
        f"<td>{INTENT_LABEL_RU.get(r['attr_id'], r['attr_id'])}</td>"
        f"<td>{num(r['search_volume_in_top'])}</td>"
        f"<td>{r['share_of_top_pct']}%</td>"
        f"<td>{r['uniq_queries']}</td>"
        f"<td>{_verdict_ru(r.get('verdict_hint') or '')}</td>"
        "</tr>"
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
            dem_line = (
                f"<span class='dem ok'>ищут в поиске Zolla"
                + (f" · примеры: {ex}" if ex else f" · объём в топе: {vol}")
                + "</span>"
            )
        elif dem == "searched_weak":
            dem_line = "<span class='dem weak'>спрос слабее — фильтр всё равно полезен на витрине</span>"
        else:
            dem_line = "<span class='dem extra'>видно на фото — можно дать как фильтр на вырост</span>"
        return (
            f"<li class='{cls}'><strong>{f.get('label')}</strong>: {f.get('value')} "
            f"<span class='ev'>({f.get('evidence')})</span> "
            f"<span class='filt'>→ фильтр: {f.get('filter_ui')}</span>"
            f"{dem_line}</li>"
        )

    case_articles = []
    for c in cases_data.get("cases") or []:
        # Partner-facing feed labels
        feed_map = {}
        for k, v in (c.get("feed") or {}).items():
            nk = (
                k.replace("(старый freeform)", "")
                .replace("(param)", "")
                .replace("как facet", "")
                .replace("(title)", "")
                .strip()
            )
            vv = str(v).replace(" (в name/extract)", "").replace(" (в name)", "").replace("extract", "карточке")
            feed_map[nk] = vv
        feed_rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in feed_map.items())
        blurb = (
            str(c.get("blurb") or "")
            .replace("extract", "карточке")
            .replace("не gap", "не новинка")
            .replace("boolean", "фильтр да/нет")
        )
        searched = c.get("searched_filters") or [
            f for f in (c.get("extracted_filters") or []) if f.get("demand_bucket") == "searched_strong"
        ]
        extra = c.get("extra_filters") or [
            f for f in (c.get("extracted_filters") or []) if f.get("demand_bucket") != "searched_strong"
        ]
        if not searched and not extra:
            searched = list(c.get("extracted_filters") or [])
        attrs_s = "".join(_attr_li(f, cls="searched") for f in searched)
        attrs_e = "".join(_attr_li(f, cls="extra") for f in extra)
        cols = "".join(
            f"<li class='coll'><strong>{x.get('label')}</strong>: {x.get('value')} "
            f"<span class='ev'>— уже было в данных карточки, не считаем новым gap</span></li>"
            for x in (c.get("collisions_not_gap") or [])
        )
        cols_block = (
            f"<h4>Уже было в карточке</h4><ul class='attrs'>{cols}</ul>" if cols else ""
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
        <div class="case-meta">Артикул {c.get('offer_id')} · <strong>{n_keep} фильтров с фото</strong></div>
        <h3>{c.get('name')}</h3>
        <p class="case-line">{blurb}</p>
        <div class="case-cols">
          <div>
            <h4>Сейчас в фиде / карточке</h4>
            <table class="mini"><tbody>{feed_rows}</tbody></table>
            {cols_block}
          </div>
          <div>
            <h4>Ищут в поиске → станет фильтром</h4>
            <ul class="attrs">{attrs_s or "<li class='ev'>нет сильного спроса из этого набора</li>"}</ul>
            <h4>Достаём с фото (на вырост)</h4>
            <ul class="attrs">{attrs_e or "<li class='ev'>—</li>"}</ul>
          </div>
        </div>
      </div>
    </article>
"""
        )
    cases_html = "".join(case_articles) or "<p class='meta'>Примеры карточек будут добавлены.</p>"

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Zolla — фильтры из картинок и описаний</title>
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
  <div class="tag">Zolla</div>
  <div class="tag">фильтры из фото и описаний</div>
  <div class="tag">исследование</div>
  <h1>Zolla: фильтры из картинок и описаний</h1>
  <p class="lead">
    Какие атрибуты стоит сделать <strong>фильтрами поиска</strong>,
    в каком формате значений, чего не хватает в фиде,
    <strong>что уже ищут покупатели</strong> и какой эффект на выручку можно ожидать.
  </p>
  <p class="meta">
    Данные: поиск Zolla за 90 дней · топ запросов · фид каталога · Яндекс.Метрика.
  </p>

  <div class="grid">
    <div class="stat"><b>{num(baseline.get('searches_90d') or 0)}</b><span>поисков за 90 дней</span></div>
    <div class="stat"><b>{num(baseline.get('uniq_queries_90d') or 0)}</b><span>уникальных запросов</span></div>
    <div class="stat"><b>{num(strong_vol)}</b><span>поисков под кандидатов в фильтры*</span></div>
    <div class="stat"><b>0</b><span>стилевых фильтров в фиде (капюшон, принт, рукав…)</span></div>
    <div class="stat"><b>{num(money['delta_revenue_rub_per_month_sketch'])} ₽</b><span>оценка доп. выручки / мес · {money.get('pct_of_search_revenue_90d')}% выручки поиска</span></div>
    <div class="stat"><b>100%</b><span>цвет и размер уже в фиде</span></div>
  </div>
  <p class="meta">* сумма объёмов по формулировкам в топе запросов; пересечения между интентами возможны.</p>

  <div class="callout">
    <strong>Короткий вывод.</strong> Фид Zolla хорошо закрывает карточку (цвет, размер, скидка),
    но не даёт фильтров визуального стиля, которые люди уже пишут в поиск:
    принт, рукав, длина, капюшон, застёжка, силуэт.
    Мы нормализуем их в фильтры с фиксированным набором значений
    («да/нет», а не свободный текст вроде «с капюшоном / капюшон есть»).
  </div>

  <h2>1. Какие атрибуты сколько ищут</h2>
  <p>
    Поиск Zolla за 90 дней: всего <strong>{num(baseline.get('searches_90d') or 0)}</strong> поисков,
    <strong>{num(baseline.get('uniq_queries_90d') or 0)}</strong> уникальных запросов.
    Ниже — что покупатели формулируют в поиске (топ запросов).
  </p>
  <table>
    <thead><tr><th>Атрибут</th><th>Объём в топе</th><th>Доля</th><th>Уник. запросов</th><th>Вывод</th></tr></thead>
    <tbody>{dem_intents}</tbody>
  </table>

  <h2>2. Что уже есть в фиде (и что не трогаем)</h2>
  <p>По выборке каталога Zolla:</p>
  <table>
    <thead><tr><th>Параметр</th><th>Заполненность</th><th>Решение</th></tr></thead>
    <tbody>
      <tr><td>Цвет</td><td>100%</td><td>не дублируем фильтром из фото</td></tr>
      <tr><td>Размер</td><td>100%</td><td>уже в вариантах товара</td></tr>
      <tr><td>Новинка / Скидка</td><td>~99–100%</td><td>операционные поля</td></tr>
      <tr><td>Капюшон / принт / рукав / застёжка / воротник / силуэт</td><td><strong>нет в фиде</strong></td><td>зона новых фильтров из фото и описаний</td></tr>
    </tbody>
  </table>
  <p class="meta">В названиях товаров слова вроде «принт», «рукав», «капюшон» встречаются,
  но это не замена фильтра: на части карточек деталь видна на фото, а в названии её нет.</p>

  <h2>3. Не предлагаем как новые фильтры</h2>
  <table>
    <thead><tr><th>Атрибут</th><th>Почему</th></tr></thead>
    <tbody>{reject_rows}</tbody>
  </table>

  <h2>4. Предлагаем сделать фильтрами</h2>
  <table>
    <thead>
      <tr>
        <th>Фильтр</th><th>Формат</th><th>Почему такой формат</th>
        <th>Спрос в поиске</th><th>Примеры запросов</th><th>Статус</th>
      </tr>
    </thead>
    <tbody>{card_rows()}</tbody>
  </table>

  <h2>5. Как выбираем формат фильтра</h2>
  <ol class="tree">
    <li>Есть спрос и значения ещё нет в фиде как нормальный фильтр?</li>
    <li>Вопрос «есть / нет» про деталь? → формат <strong>да / нет</strong> (капюшон, карманы).</li>
    <li>Есть стандартный набор взаимоисключающих вариантов? → <strong>один из списка</strong>
      (длина mini/midi/maxi; рукав короткий/длинный/без рукавов).</li>
    <li>Несколько значений сразу возможны? → <strong>несколько из списка</strong> (принт).</li>
  </ol>
  <div class="callout">
    Пример: капюшон — не свободный текст, а фильтр «да / нет», потому что покупательский вопрос бинарный
    («куртка с капюшоном»).
  </div>

  <h2>6. Примеры: фото → фильтр</h2>
  <p class="lead" style="font-size:15px">
    Реальные карточки Zolla. Слева — что уже в фиде.
    Справа — что достаём с фото: сначала то, что <strong>ищут</strong>,
    затем то, что можно дать <strong>как фильтр на вырост</strong>.
  </p>
  {cases_html}

  <h2>7. Деньги</h2>
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
      <tr><td>Ожидаемый прирост конверсии на затронутых визитах</td><td>+{int(((money.get('assumptions') or {}).get('relative_cvr_lift_base') or 0)*100)}% относительно
        (≈ +{(money.get('assumptions') or {}).get('cvr_lift_pp_base')} п.п. к текущим {(money.get('baseline_money') or {}).get('search_cvr_pct')}%)
        — бенчмарк «сессии с фильтрами / без»</td></tr>
      <tr><td>Доля затронутых визитов с поиском (базовый сценарий)</td><td>{int(((money.get('assumptions') or {}).get('addressable_share_base') or 0)*100)}%</td></tr>
      <tr><td>Доля пользователей новых фильтров среди затронутых</td><td>{int(((money.get('assumptions') or {}).get('adoption_base') or 0)*100)}%</td></tr>
      <tr><td>Как считаем</td><td>{money.get('formula')}</td></tr>
      <tr><td><strong>Оценка доп. выручки / мес</strong></td><td><strong>{num(money['delta_revenue_rub_per_month_sketch'])} ₽</strong>
        · <strong>{money.get('pct_of_search_revenue_90d')}%</strong> выручки из поиска</td></tr>
      <tr><td>Оценка доп. выручки / 90 дней</td><td>{num(money['delta_revenue_rub_per_90d_sketch'])} ₽
        · ≈ {num((money.get('scenarios') or {}).get('base', {}).get('extra_orders_90d') or 0)} доп. заказов</td></tr>
      <tr><td>Диапазон сценариев / мес</td><td>
        осторожный {num((money.get('scenarios') or {}).get('conservative', {}).get('delta_revenue_rub_month') or 0)} ₽
        ({(money.get('scenarios') or {}).get('conservative', {}).get('pct_of_search_revenue_90d')}%) ·
        оптимистичный {num((money.get('scenarios') or {}).get('optimistic', {}).get('delta_revenue_rub_month') or 0)} ₽
        ({(money.get('scenarios') or {}).get('optimistic', {}).get('pct_of_search_revenue_90d')}%)
      </td></tr>
    </tbody>
  </table>
  <p class="meta">После запуска фильтров заменим оценку на замер конверсии с фильтрами и без на данных Zolla.</p>

  <h2>8. Что уже готово</h2>
  <ul>
    <li>Нормализованные значения фильтров (закрытый список, без «каши» из формулировок).</li>
    <li>Один раз разбираем картинку — значения переносятся на все размеры с тем же фото.</li>
    <li>Пилот по ключевым фильтрам (капюшон, длина, рукав, принт, застёжка и др.) на реальных карточках Zolla.</li>
  </ul>

  <footer>
    Подготовлено для Zolla · фильтры из фото и описаний
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
