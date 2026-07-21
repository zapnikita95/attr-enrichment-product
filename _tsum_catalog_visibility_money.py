# -*- coding: utf-8 -*-
"""
TSUM — отдельный стрим денег: каталог × поиск по категориям × P(новый attr)
→ доп. появление товаров в выдаче → ₽ (conservative / optimistic).

Не заменяет query-stream (RESERVE/NORMAL × ΔCVR). Это visibility/recall upside.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"

# Бакеты: slug каталога + keywords для классификации запросов
BUCKETS = {
    "odezhda": {
        "label": "Одежда (без верхней)",
        "slugs": (
            "odezhda",
            "platya",
            "rubashki",
            "futbolki",
            "bryuki",
            "dzhinsy",
            "yubki",
            "belye",
            "bele",
            "svitery",
            "tolstovki",
            "hudi",
            "kostyumy",
        ),
        "exclude_slugs": ("verkhnyaya",),
        "q_keywords": (
            "плать",
            "рубаш",
            "футбол",
            "брюк",
            "джинс",
            "юбк",
            "костюм",
            "свитер",
            "худи",
            "толстов",
            "блуз",
            "пиджак",
            "кардиган",
            "водолаз",
            "лонгслив",
            "шорт",
            "леггинс",
            "комбинезон",
        ),
        # P(SKU получит ≥1 новый searchable vision-attr), гипотеза на KEEP + gap фида
        "p_extract": {"conservative": 0.28, "optimistic": 0.52},
        # Доля SKU, у которых такой attr уже в индексе/фиде (pattern coverage ~2.7% + редкие params)
        "coverage_now": {"conservative": 0.10, "optimistic": 0.04},
        "attr_families_direct": [
            "Принт / узор",
            "Силуэт / посадка",
            "Застёжка / детали",
            "Воротник / вырез",
        ],
        "attr_families_expanded": [
            "Посадка и силуэт одежды",
            "Принт и орнамент",
            "Декор и фактура",
        ],
        "attr_demand_share": {"direct_facet": 1.0, "expanded_style": 0.80},
    },
    "verhnyaya": {
        "label": "Верхняя одежда",
        "slugs": ("verkhnyaya", "kurtki", "palto", "plashchi", "dublyenki", "shuby"),
        "exclude_slugs": (),
        "q_keywords": (
            "куртк",
            "пальто",
            "плащ",
            "пуховик",
            "парк",
            "тренч",
            "бомбер",
            "ветровк",
            "дублён",
            "шуб",
            "капюшон",
        ),
        "p_extract": {"conservative": 0.35, "optimistic": 0.60},
        "coverage_now": {"conservative": 0.12, "optimistic": 0.05},
        "attr_families_direct": ["Капюшон"],
        "attr_families_expanded": ["Декор и фактура"],
        "attr_demand_share": {"direct_facet": 1.0, "expanded_style": 0.20},
    },
    "obuv": {
        "label": "Обувь",
        "slugs": ("obuv", "tufli", "krossovki", "bosonozhki", "sapogi", "botinki", "lofery"),
        "exclude_slugs": (),
        "q_keywords": (
            "туфл",
            "кроссов",
            "босонож",
            "сапог",
            "ботин",
            "лофер",
            "мюли",
            "каблук",
            "танкет",
            "платформ",
            "слингбэк",
            "балетк",
            "кед",
            "мокасин",
            "шлеп",
            "сланц",
            "вьетнам",
        ),
        "p_extract": {"conservative": 0.40, "optimistic": 0.70},
        "coverage_now": {"conservative": 0.15, "optimistic": 0.06},
        "attr_families_direct": ["Обувь: каблук / платформа"],
        "attr_families_expanded": ["Каблук и обувные формы"],
        "attr_demand_share": {"direct_facet": 1.0, "expanded_style": 1.0},
    },
    "sumki": {
        "label": "Сумки",
        "slugs": ("sumki", "sumka", "klatch", "ryukzaki"),
        "exclude_slugs": (),
        "q_keywords": (
            "сумк",
            "клатч",
            "тоут",
            "шоппер",
            "хобо",
            "кроссбоди",
            "рюкзак",
            "портфел",
            "кошел",
            "картхолдер",
        ),
        "p_extract": {"conservative": 0.45, "optimistic": 0.75},
        "coverage_now": {"conservative": 0.18, "optimistic": 0.08},
        "attr_families_direct": ["Тип сумки"],
        "attr_families_expanded": ["Сумки по силуэту"],
        "attr_demand_share": {"direct_facet": 1.0, "expanded_style": 1.0},
    },
    "parfyum": {
        "label": "Парфюмерия",
        "slugs": ("parfyumeriya", "parfumeriya"),
        "exclude_slugs": (),
        "q_keywords": ("парфюм", "туалетная вода", "духи", "одеколон", "аромат"),
        "p_extract": {"conservative": 0.15, "optimistic": 0.35},
        "coverage_now": {"conservative": 0.25, "optimistic": 0.12},
        "attr_families_direct": ["Парфюм: ноты / концентрация"],
        "attr_families_expanded": ["Парфюмерия descriptive"],
        "attr_demand_share": {"direct_facet": 1.0, "expanded_style": 1.0},
    },
    "aksessuary": {
        "label": "Аксессуары / очки / часы",
        "slugs": (
            "aksessuary",
            "ochki",
            "chasy",
            "remni",
            "galstuki",
            "platki",
            "bizhuteriya",
            "yuvelirnye",
            "ukrasheniya",
        ),
        "exclude_slugs": (),
        "q_keywords": (
            "очк",
            "час",
            "ремень",
            "ремни",
            "галстук",
            "платок",
            "шарф",
            "бижутер",
            "кольц",
            "серьг",
            "браслет",
            "колье",
        ),
        "p_extract": {"conservative": 0.20, "optimistic": 0.40},
        "coverage_now": {"conservative": 0.12, "optimistic": 0.05},
        "attr_families_direct": [],
        "attr_families_expanded": [],
        "attr_demand_share": {"direct_facet": 1.0, "expanded_style": 1.0},
    },
}

# Воронка: новый attr → товар в выдаче → клик → покупка
FUNNEL = {
    "conservative": {
        # Среди attr-запросов категории: доля сессий, где ≥1 новообогащённый SKU
        # реально попадает в top выдачи (не все eligible сразу в SERP)
        "p_enters_serp_given_eligible": 0.22,
        "ctr_new_slot": 0.045,
        "purchase_given_click": 0.045,
        "attr_demand_source": "direct_facet",
        # Какая доля family-спроса реально «закрывается» новым vision-attr
        # (direct facet почти весь; expanded type-nouns частично уже в фиде)
        "attr_gated_share_of_family_demand": 0.85,
        "fallback_attr_share_of_cat_search": 0.04,
        "p_session_cap": 0.45,
    },
    "optimistic": {
        "p_enters_serp_given_eligible": 0.35,
        "ctr_new_slot": 0.065,
        "purchase_given_click": 0.060,
        "attr_demand_source": "expanded_style",
        # expanded_style содержит много type-запросов (мюли, босоножки) — уже в name/типе
        "attr_gated_share_of_family_demand": 0.35,
        "fallback_attr_share_of_cat_search": 0.10,
        "p_session_cap": 0.55,
    },
}


def _slug_from_url(url: str) -> str:
    # tsum: /catalog/verkhnyaya-odezhda-18424/ → verkhnyaya-odezhda
    m = re.search(r"/catalog/([a-z0-9_-]+)-(\d+)/?", (url or "").lower())
    return m.group(1) if m else ""


def offers_by_bucket(inv: dict) -> dict[str, dict]:
    cats = inv.get("top_categories_by_offers") or []
    out: dict[str, dict] = {
        bid: {"offers": 0, "categories": []} for bid in BUCKETS
    }
    assigned = set()
    for c in cats:
        url = c.get("url") or ""
        slug = _slug_from_url(url)
        name = (c.get("name") or "").lower()
        cid = c.get("id")
        for bid, meta in BUCKETS.items():
            if any(ex in slug for ex in meta["exclude_slugs"]):
                if bid == "odezhda":
                    continue
            hit = any(s in slug for s in meta["slugs"])
            if not hit and bid == "odezhda":
                # детская одежда и т.п. по имени
                hit = "одежд" in name and "верхн" not in name
            if hit:
                out[bid]["offers"] += int(c.get("offers") or 0)
                out[bid]["categories"].append(
                    {"id": cid, "name": c.get("name"), "offers": c.get("offers"), "slug": slug}
                )
                assigned.add(cid)
                break
    return out


def classify_queries_to_buckets(queries: list[dict]) -> dict[str, dict]:
    """Грубая разметка top-N запросов → бакет (первый match)."""
    stats = {
        bid: {"searches_90d": 0, "queries": 0, "examples": []} for bid in BUCKETS
    }
    other = {"searches_90d": 0, "queries": 0}
    brandish = 0
    for row in queries:
        q = (row.get("q") or "").lower()
        cnt = int(row.get("cnt") or 0)
        matched = None
        for bid, meta in BUCKETS.items():
            if any(kw in q for kw in meta["q_keywords"]):
                matched = bid
                break
        if matched is None:
            # бренд/прочее
            other["searches_90d"] += cnt
            other["queries"] += 1
            if re.fullmatch(r"[a-z0-9 &\-\.']{2,40}", q):
                brandish += cnt
            continue
        stats[matched]["searches_90d"] += cnt
        stats[matched]["queries"] += 1
        if len(stats[matched]["examples"]) < 6:
            stats[matched]["examples"].append({"q": row.get("q"), "cnt": cnt})
    return {
        "by_bucket": stats,
        "other_searches_90d": other["searches_90d"],
        "other_queries": other["queries"],
        "likely_brand_searches_in_other_90d": brandish,
    }


def family_searches(qi: dict, family_names: list[str], tier: str) -> tuple[int, list[dict]]:
    tier_data = (qi.get("tiers") or {}).get(tier) or {}
    families = tier_data.get("families") or {}
    total = 0
    used = []
    for name in family_names:
        # exact or fuzzy contains
        hit = None
        if name in families:
            hit = families[name]
        else:
            for fk, fv in families.items():
                if name.lower() in fk.lower() or fk.lower() in name.lower():
                    hit = fv
                    break
        if not hit:
            continue
        s = int(hit.get("searches_90d") or 0)
        total += s
        used.append({"family": name, "searches_90d": s})
    return total, used


def compute_scenario(
    scenario: str,
    bucket_offers: dict,
    cat_search: dict,
    qi: dict,
    aov: float,
) -> dict:
    funnel = FUNNEL[scenario]
    tier = funnel["attr_demand_source"]
    rows = []
    total_rev_90 = 0.0
    total_extra_impr = 0.0
    total_extra_clicks = 0.0
    total_extra_purch = 0.0
    total_attr_demand = 0

    for bid, meta in BUCKETS.items():
        offers = int(bucket_offers[bid]["offers"])
        cat_s = int(cat_search["by_bucket"][bid]["searches_90d"])
        fam_names = (
            meta["attr_families_direct"]
            if tier == "direct_facet"
            else meta["attr_families_expanded"]
        )
        attr_demand_raw, fam_used = family_searches(qi, fam_names, tier)
        share = float((meta.get("attr_demand_share") or {}).get(tier) or 1.0)
        gated = float(funnel["attr_gated_share_of_family_demand"])
        attr_demand = int(attr_demand_raw * share * gated)
        if attr_demand <= 0:
            # fallback: доля category-search
            attr_demand = int(cat_s * funnel["fallback_attr_share_of_cat_search"])
            fam_used = [{"family": "_fallback_share_of_category_search", "searches_90d": attr_demand}]
        else:
            for fu in fam_used:
                fu["searches_allocated"] = int(int(fu["searches_90d"]) * share * gated)

        p_ex = meta["p_extract"][scenario]
        cov = meta["coverage_now"][scenario]
        newly_eligible_share = max(0.0, p_ex * (1.0 - cov))

        # P(сессия attr-запроса получает ≥1 новый SKU в выдаче):
        # newly_eligible × коэффициент «попадания в top» (не все eligible сразу в SERP)
        p_session_new_sku = min(
            float(funnel["p_session_cap"]),
            newly_eligible_share * funnel["p_enters_serp_given_eligible"] / 0.30,
        )

        # Extra impressions: 1 новый слот на benefiting session
        extra_impr = attr_demand * p_session_new_sku
        extra_clicks = extra_impr * funnel["ctr_new_slot"]
        extra_purch = extra_clicks * funnel["purchase_given_click"]
        rev_90 = extra_purch * aov

        total_rev_90 += rev_90
        total_extra_impr += extra_impr
        total_extra_clicks += extra_clicks
        total_extra_purch += extra_purch
        total_attr_demand += attr_demand

        rows.append(
            {
                "bucket": bid,
                "label": meta["label"],
                "offers": offers,
                "category_searches_90d": cat_s,
                "attr_demand_searches_90d": attr_demand,
                "attr_demand_source": tier,
                "families_used": fam_used,
                "p_extract": p_ex,
                "coverage_now": cov,
                "newly_eligible_sku_share": round(newly_eligible_share, 4),
                "p_session_gets_new_sku_in_serp": round(p_session_new_sku, 4),
                "extra_impressions_90d": round(extra_impr),
                "extra_clicks_90d": round(extra_clicks),
                "extra_purchases_90d": round(extra_purch, 2),
                "revenue_90d": round(rev_90),
                "revenue_month": round(rev_90 / 3),
                "revenue_year": round(rev_90 / 3 * 12),
                "new_indexable_skus_est": round(offers * newly_eligible_share),
            }
        )

    rows.sort(key=lambda r: -r["revenue_month"])
    return {
        "scenario": scenario,
        "funnel": funnel,
        "aov": round(aov),
        "totals": {
            "attr_demand_searches_90d": total_attr_demand,
            "extra_impressions_90d": round(total_extra_impr),
            "extra_clicks_90d": round(total_extra_clicks),
            "extra_purchases_90d": round(total_extra_purch, 2),
            "revenue_90d": round(total_rev_90),
            "revenue_month": round(total_rev_90 / 3),
            "revenue_year": round(total_rev_90 / 3 * 12),
        },
        "by_bucket": rows,
    }


def write_md(report: dict) -> str:
    c = report["scenarios"]["conservative"]
    o = report["scenarios"]["optimistic"]
    lines = []
    lines.append("# ЦУМ — стрим B: деньги от доп. появления в выдаче\n")
    lines.append("\n> Отдельно от query-stream (RESERVE/NORMAL × ΔCVR).  \n")
    lines.append("> Здесь: **категории × P(новый attr на SKU) × товар попадает в SERP** → клик → покупка.\n")
    lines.append("\n## Итог\n\n")
    lines.append("| Сценарий | ₽/мес | ₽/90д | ₽/год | доп. показы/90д | доп. покупки/90д |\n")
    lines.append("|---|---:|---:|---:|---:|---:|\n")
    lines.append(
        f"| Консервативный | {c['totals']['revenue_month']:,} | {c['totals']['revenue_90d']:,} | "
        f"{c['totals']['revenue_year']:,} | {c['totals']['extra_impressions_90d']:,} | "
        f"{c['totals']['extra_purchases_90d']:,} |\n"
    )
    lines.append(
        f"| Оптимистичный | {o['totals']['revenue_month']:,} | {o['totals']['revenue_90d']:,} | "
        f"{o['totals']['revenue_year']:,} | {o['totals']['extra_impressions_90d']:,} | "
        f"{o['totals']['extra_purchases_90d']:,} |\n"
    )
    lines.append("\n## Формула\n\n```text\n")
    lines.append("attr_demand = family_searches × bucket_share × attr_gated_share\n")
    lines.append("newly_eligible = p_extract × (1 − coverage_now)\n")
    lines.append("p_session_new_sku_in_serp = min(cap, newly_eligible × serp_factor)\n")
    lines.append("extra_impressions = attr_demand × p_session_new_sku_in_serp\n")
    lines.append("extra_clicks = extra_impressions × CTR_new_slot\n")
    lines.append("extra_purchases = extra_clicks × purchase|click\n")
    lines.append("Δ₽_90д = extra_purchases × AOV_Метрика\n")
    lines.append("```\n\n")
    lines.append(
        f"AOV = **{report['aov']:,} ₽** (поиск, Метрика). "
        "Conservative: `direct_facet` × gated 85%. "
        "Optimistic: `expanded_style` × gated 35% (type-nouns вроде «мюли» часто уже в фиде).\n"
    )
    lines.append("\n## Поиск по категориям (top-30k CH, keyword map)\n\n")
    lines.append("| Категория | Поисков/90д | SKU (оценка) |\n|---|---:|---:|\n")
    for bid, meta in BUCKETS.items():
        s = report["category_search"]["by_bucket"][bid]["searches_90d"]
        offers = report["catalog"][bid]["offers"]
        lines.append(f"| {meta['label']} | {s:,} | {offers:,} |\n")
    lines.append(
        f"| Прочее (бренды и т.п.) | {report['category_search']['other_searches_90d']:,} | — |\n"
    )
    lines.append("\n## Conservative — по бакетам\n\n")
    lines.append("| Категория | Attr-спрос/90д | P(extract) | Eligible SKU% | ₽/мес |\n|---|---:|---:|---:|---:|\n")
    for r in c["by_bucket"]:
        lines.append(
            f"| {r['label']} | {r['attr_demand_searches_90d']:,} | {r['p_extract']:.0%} | "
            f"{r['newly_eligible_sku_share']:.1%} | {r['revenue_month']:,} |\n"
        )
    lines.append("\n## Optimistic — по бакетам\n\n")
    lines.append("| Категория | Attr-спрос/90д | P(extract) | Eligible SKU% | ₽/мес |\n|---|---:|---:|---:|---:|\n")
    for r in o["by_bucket"]:
        lines.append(
            f"| {r['label']} | {r['attr_demand_searches_90d']:,} | {r['p_extract']:.0%} | "
            f"{r['newly_eligible_sku_share']:.1%} | {r['revenue_month']:,} |\n"
        )
    lines.append("\n## Важно для партнёра\n\n")
    lines.append(
        "- Это **гипотетический** visibility-стрим: не складывать 1:1 с query-stream без оговорок "
        "(частичное пересечение спроса).\n"
    )
    lines.append(
        "- Смысл: товары с новыми attr **начинают матчиться** в выдаче → доп. показы/клики/покупки.\n"
    )
    lines.append(
        "- Консерватив: узкий facet-спрос + ниже P(extract)/CTR. "
        "Оптимист: расширенный style-спрос + выше воронка.\n"
    )
    return "".join(lines)


def patch_html(report: dict) -> None:
    import re as _re

    html_path = OUT / "tsum-image-attrs-research.html"
    if not html_path.exists():
        return
    html = html_path.read_text(encoding="utf-8")
    c = report["scenarios"]["conservative"]["totals"]
    o = report["scenarios"]["optimistic"]["totals"]
    rows_c = report["scenarios"]["conservative"]["by_bucket"]
    rows_o = report["scenarios"]["optimistic"]["by_bucket"]

    def fmt_m(n: float) -> str:
        if abs(n) >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if abs(n) >= 1_000:
            return f"{n/1_000:.0f}k"
        return str(int(n))

    tr_c = "".join(
        f"<tr><td>{r['label']}</td><td>{r['offers']:,}</td>"
        f"<td>{r['category_searches_90d']:,}</td>"
        f"<td>{r['attr_demand_searches_90d']:,}</td>"
        f"<td>{r['p_extract']:.0%}</td>"
        f"<td>{r['newly_eligible_sku_share']:.0%}</td>"
        f"<td>+{fmt_m(r['revenue_month'])}</td></tr>"
        for r in rows_c
    )
    tr_o = "".join(
        f"<tr><td>{r['label']}</td><td>{r['offers']:,}</td>"
        f"<td>{r['attr_demand_searches_90d']:,}</td>"
        f"<td>{r['p_extract']:.0%}</td>"
        f"<td>+{fmt_m(r['revenue_month'])}</td></tr>"
        for r in rows_o
    )
    block = f"""  <h2>8b. Доп. потенциал: товары появляются в выдаче (стрим B)</h2>
  <p class="lead" style="font-size:15px">
    Это <strong>не замена</strong> базе стрима A, а <strong>второй слой денег</strong>.
    Считаем по категориям: сколько ищут → с какой вероятностью на SKU появится новый vision-attr →
    товар <em>впервые матчится</em> в выдаче → доп. показы / клики / покупки.
  </p>
  <div class="grid">
    <div class="stat"><b>+{fmt_m(c['revenue_month'])} ₽</b><span>консерватив · доп. ₽/мес</span></div>
    <div class="stat"><b>+{fmt_m(o['revenue_month'])} ₽</b><span>оптимист · доп. ₽/мес</span></div>
    <div class="stat"><b>+{fmt_m(c['revenue_year'])}–{fmt_m(o['revenue_year'])} ₽</b><span>доп. ₽/год (cons→opt)</span></div>
    <div class="stat"><b>{c['extra_impressions_90d']:,}–{o['extra_impressions_90d']:,}</b><span>доп. показы / 90д</span></div>
  </div>
  <div class="callout">
    <strong>Как читать партнёру.</strong>
    База (стрим A) = лучше находим то, что уже ищут стилем.
    Доп. потенциал (стрим B) = каталог «открывается» в выдаче.
    Не складывать A+B в одну цифру без пометки «частичное пересечение».
  </div>
  <h3>Conservative — где лежит доп. потенциал</h3>
  <table>
    <thead><tr><th>Категория</th><th>SKU</th><th>Поиск кат./90д</th><th>Attr-спрос</th><th>P(новый attr)</th><th>Eligible%</th><th>доп. ₽/мес</th></tr></thead>
    <tbody>{tr_c}</tbody>
  </table>
  <h3>Optimistic (сжато)</h3>
  <table>
    <thead><tr><th>Категория</th><th>SKU</th><th>Attr-спрос</th><th>P(новый attr)</th><th>доп. ₽/мес</th></tr></thead>
    <tbody>{tr_o}</tbody>
  </table>
  <p class="meta">
    Формула B: <code>attr_demand × P(extract)×(1−coverage) × P(в SERP) × CTR × purchase|click × AOV</code>.
    Детали: <code>MONEY_CATALOG_VISIBILITY.md</code>.
  </p>
"""
    start = "<!-- CATALOG_VISIBILITY_STREAM -->"
    end = "<!-- /CATALOG_VISIBILITY_STREAM -->"
    wrapped = f"{start}\n{block}\n{end}\n"
    html = _re.sub(
        _re.escape(start) + r".*?" + _re.escape(end) + r"\n?",
        "",
        html,
        flags=_re.S,
    )
    html = _re.sub(
        r"<h2>8b\. Доп\. потенциал:.*?(?=<h2>9\.|\Z)",
        "",
        html,
        flags=_re.S,
    )
    anchor = "<h2>9. Методология (коротко)</h2>"
    if anchor in html:
        html = html.replace(anchor, wrapped + "\n" + anchor)
    else:
        html += "\n" + wrapped

    html_path.write_text(html, encoding="utf-8")


def main() -> None:
    inv = json.loads((OUT / "feed_inventory.json").read_text(encoding="utf-8"))
    qi = json.loads((OUT / "query_impact_refined.json").read_text(encoding="utf-8"))
    top = json.loads((OUT / "top-30k-queries-ch.json").read_text(encoding="utf-8"))
    met = {}
    mp = OUT / "metrika_cvr_clean.json"
    if mp.exists():
        met = json.loads(mp.read_text(encoding="utf-8"))
    aov = float((met.get("with_search") or {}).get("aov") or 106731)

    bucket_offers = offers_by_bucket(inv)
    cat_search = classify_queries_to_buckets(top.get("queries") or [])

    scenarios = {
        "conservative": compute_scenario("conservative", bucket_offers, cat_search, qi, aov),
        "optimistic": compute_scenario("optimistic", bucket_offers, cat_search, qi, aov),
    }

    report = {
        "stream": "B_catalog_visibility",
        "partner": "TSUM",
        "site_id": 203,
        "note": (
            "Отдельный стрим от query ΔCVR. Деньги = доп. показы товаров в выдаче "
            "после индексации vision-атрибутов. Гипотеза; не суммировать 1:1 со стримом A."
        ),
        "formula": (
            "newly_eligible=p_extract*(1-coverage); "
            "extra_impr=attr_demand*min(0.70, newly_eligible*serp_factor); "
            "Δ₽=extra_impr*CTR*purchase|click*AOV"
        ),
        "aov": round(aov),
        "metrika_cvr_search_pct": (met.get("with_search") or {}).get("cvr_pct"),
        "catalog": {
            bid: {
                "label": BUCKETS[bid]["label"],
                "offers": bucket_offers[bid]["offers"],
                "n_categories_rolled_up": len(bucket_offers[bid]["categories"]),
            }
            for bid in BUCKETS
        },
        "category_search": cat_search,
        "hypotheses": {
            bid: {
                "p_extract": BUCKETS[bid]["p_extract"],
                "coverage_now": BUCKETS[bid]["coverage_now"],
            }
            for bid in BUCKETS
        },
        "funnel": FUNNEL,
        "scenarios": scenarios,
        "vs_stream_a": {
            "stream_a": "RESERVE/NORMAL × fixable × ΔCVR × AOV (money_impact_metrika.json)",
            "stream_b": "this file",
            "combine_guidance": (
                "Показывать раздельно. Верхняя оценка портфеля ≈ A + часть B; "
                "полный A+B завысит из-за общего attr-спроса."
            ),
        },
    }

    (OUT / "money_catalog_visibility.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = write_md(report)
    (OUT / "MONEY_CATALOG_VISIBILITY.md").write_text(md, encoding="utf-8")
    patch_html(report)

    # append pointer to MONEY_IMPACT.md
    mi = OUT / "MONEY_IMPACT.md"
    if mi.exists():
        text = mi.read_text(encoding="utf-8")
        pointer = (
            "\n\n## Стрим B (отдельно): каталог → выдача\n\n"
            f"- Консерватив: **{scenarios['conservative']['totals']['revenue_month']:,} ₽/мес**\n"
            f"- Оптимист: **{scenarios['optimistic']['totals']['revenue_month']:,} ₽/мес**\n"
            "- Детали: `MONEY_CATALOG_VISIBILITY.md`, `money_catalog_visibility.json`\n"
        )
        if "Стрим B" not in text:
            mi.write_text(text.rstrip() + pointer, encoding="utf-8")
        else:
            import re as _re

            mi.write_text(
                _re.sub(
                    r"\n## Стрим B \(отдельно\):.*",
                    pointer.rstrip(),
                    text,
                    count=1,
                    flags=_re.S,
                ),
                encoding="utf-8",
            )

    print(
        json.dumps(
            {
                "conservative_month": scenarios["conservative"]["totals"]["revenue_month"],
                "optimistic_month": scenarios["optimistic"]["totals"]["revenue_month"],
                "conservative_year": scenarios["conservative"]["totals"]["revenue_year"],
                "optimistic_year": scenarios["optimistic"]["totals"]["revenue_year"],
                "by_bucket_cons": [
                    (r["label"], r["revenue_month"], r["attr_demand_searches_90d"])
                    for r in scenarios["conservative"]["by_bucket"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
