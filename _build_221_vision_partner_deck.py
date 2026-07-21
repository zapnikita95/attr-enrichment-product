# -*- coding: utf-8 -*-
"""Build partner HTML deck: 221 vision attrs + money (CH searches × uplift from existing 221 study)."""
from __future__ import annotations

import csv
import json
import re
import urllib3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

urllib3.disable_warnings()

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "portfolio" / "221_azbuka"
DESK = Path(r"C:\Users\1\OneDrive\Desktop")
CSV = DESK / "221_azbuka_vision_dashboard_upload.csv"
KEEP = OUT / "vision_batch_keep.json"
SUMMARY = OUT / "vision_batch_summary.json"
TEXT_IMPACT = OUT / "_zip_peek" / "221_azbuka_partner_impact" / "221_azbuka_attr_impact_data.json"

CH_URL = "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443"
CH_AUTH = ("digi-admin", "Fl2bSowt")
SITE_ID = 221
API_KEY = "5BZ4H1HRDU"

# From text-impact study (same partner/period methodology)
AOV = 6192.55
ORDER_EXACT = 0.14104
ORDER_FALLBACK = 0.11774
ORDER_ZERO = 0.05263
UPLIFT_FB = ORDER_EXACT - ORDER_FALLBACK  # ~0.0233
UPLIFT_ZERO = ORDER_EXACT - ORDER_ZERO  # ~0.08841


def ch_query(sql: str, timeout: int = 120) -> list[dict]:
    r = requests.post(
        CH_URL,
        auth=CH_AUTH,
        params={"query": sql + " FORMAT JSON", "database": "sessions"},
        timeout=timeout,
        verify=False,
    )
    if r.status_code != 200:
        print("CH ERR", r.status_code, r.text[:400])
        return []
    return r.json().get("data") or []


def load_vision_rows() -> list[dict]:
    rows = []
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "external_id": (r.get("external_id") or "").strip(),
                    "offer_name": (r.get("offer_name") or "").strip(),
                    "attribute_name": (r.get("attribute_name") or "").strip(),
                    "attribute_value": (r.get("attribute_value") or "").strip(),
                    "product_type": (r.get("product_type") or "").strip(),
                    "path": (r.get("feed_category_path") or "").strip(),
                }
            )
    return rows


def normalize(s: str) -> str:
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"[^a-zа-я0-9\s]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Head nouns that appear in flavor strings but are NOT vision-specific signals
STOP_MATCH = {
    "торт",
    "молоко",
    "сыр",
    "чай",
    "кофе",
    "хлеб",
    "вино",
    "вода",
    "мясо",
    "рыба",
    "курица",
    "масло",
    "сок",
    "суп",
    "салат",
    "рис",
    "мука",
    "мед",
    "мёд",
    "яйца",
    "икра",
    "колбаса",
    "йогурт",
    "творог",
    "сметана",
    "шоколад",
    "печенье",
    "мороженое",
    "чипсы",
    "паста",
    "соус",
    "крем",
    "пакет",
    "банка",
    "бутылка",
    "коробка",
    "упаковка",
    "продукт",
    "вкус",
    "аромат",
    "классический",
    "натуральный",
    "оригинальный",
}

# Strong packshot signals worth attributing even as single-token queries
STRONG_SIGNALS = {
    "мельница",
    "дойпак",
    "пауч",
    "ломтики",
    "ломтик",
    "кусочки",
    "засахаренные",
    "засахаренный",
    "hand",
    "cooked",
    "брауни",
    "brownie",
    "пюре",
    "гранулы",
    "хлопья",
}


def distinctive_tokens(val: str) -> list[str]:
    toks = []
    for t in normalize(val).split():
        if t in STRONG_SIGNALS:
            toks.append(t)
            continue
        if t in STOP_MATCH:
            continue
        if len(t) >= 5:
            toks.append(t)
    return toks


def fetch_top_queries(limit: int = 20000) -> list[tuple[str, int]]:
    rows = ch_query(
        f"""
SELECT lowerUTF8(searchTerm) AS q, count() AS c
FROM sessions.searches
WHERE siteId = {SITE_ID}
  AND toDate(timestamp) >= today() - 90
  AND toDate(timestamp) <= today() - 1
  AND searchTerm != ''
GROUP BY q
ORDER BY c DESC
LIMIT {limit}
"""
    )
    out = []
    for r in rows:
        q = str(r.get("q") or "").strip()
        c = int(float(r.get("c") or 0))
        if q and c > 0:
            out.append((q, c))
    return out


def fetch_baseline() -> dict:
    sess = ch_query(
        f"""
SELECT
  count() AS sessions,
  countIf(searches > 0 OR autocompleteClicks > 0) AS with_search,
  sum(withOrder) AS orders,
  round(sumIf(revenue, withOrder > 0), 2) AS revenue
FROM sessions.agg_sessions
WHERE siteId = {SITE_ID}
  AND toDate(timeBegin) >= today() - 90
  AND toDate(timeBegin) <= today() - 1
"""
    )
    searches = ch_query(
        f"""
SELECT count() AS searches
FROM sessions.searches
WHERE siteId = {SITE_ID}
  AND toDate(timestamp) >= today() - 90
  AND toDate(timestamp) <= today() - 1
"""
    )
    base = sess[0] if sess else {}
    base["searches_90d"] = int(float((searches[0] if searches else {}).get("searches") or 0))
    return base


def match_queries(queries: list[tuple[str, int]], vision_rows: list[dict]) -> list[dict]:
    """Strict: query must contain distinctive vision token/phrase (not bare category nouns)."""
    inv: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    phrases: list[tuple[str, str, str, str]] = []
    for r in vision_rows:
        for t in distinctive_tokens(r["attribute_value"]):
            inv[t].append((r["attribute_name"], r["attribute_value"], r["external_id"]))
        vn = normalize(r["attribute_value"])
        toks = vn.split()
        # multi-word flavor/form only
        if len(toks) >= 2 and 6 <= len(vn) <= 36 and not all(t in STOP_MATCH for t in toks):
            phrases.append((vn, r["attribute_name"], r["attribute_value"], r["external_id"]))

    hits = []
    for q, c in queries:
        qn = normalize(q)
        q_toks = qn.split()
        if len(qn) < 4:
            continue
        # skip pure category head nouns
        if len(q_toks) == 1 and q_toks[0] in STOP_MATCH:
            continue

        matched: list[tuple[str, str, str]] = []

        # phrase: full attr value inside query (query longer / equal)
        for vn, an, av, oid in phrases:
            if vn == qn or (len(vn) >= 6 and vn in qn):
                matched.append((an, av, oid))

        # token: distinctive signal appears in query
        for t, items in inv.items():
            if t in q_toks or (len(t) >= 6 and t in qn):
                # single-token query only if strong signal
                if len(q_toks) == 1 and t not in STRONG_SIGNALS:
                    continue
                matched.extend(items[:3])

        if not matched:
            continue
        seen = set()
        uniq = []
        for an, av, oid in matched:
            key = (an, normalize(av))
            if key in seen:
                continue
            seen.add(key)
            uniq.append({"attribute_name": an, "attribute_value": av, "offer_id": oid})
        hits.append({"query": q, "frequency_90d": c, "matches": uniq[:6]})
    hits.sort(key=lambda x: -x["frequency_90d"])
    return hits


def money_from_matches(hits: list[dict]) -> dict:
    """Conservative money: only attribute-shaped demand (2+ tokens or strong signal)."""
    freq_strong = 0  # мельница / дойпак / hand cooked…
    freq_attr = 0  # multi-token flavor/form queries
    for h in hits:
        q = h["query"]
        f = h["frequency_90d"]
        toks = q.split()
        if any(t in STRONG_SIGNALS for t in toks):
            freq_strong += f
        elif len(toks) >= 2:
            freq_attr += f
        # ignore residual single-token weak matches

    # 90d → month
    strong_m = freq_strong / 3
    attr_m = freq_attr / 3

    # Strong pack signals closer to reserve→exact (half uplift)
    rev_strong = strong_m * (UPLIFT_FB * 0.5) * AOV
    # Multi-token flavor: smaller precision uplift 0.8pp
    rev_attr = attr_m * 0.008 * AOV

    rev_strong_opt = strong_m * UPLIFT_FB * AOV
    rev_attr_opt = attr_m * 0.015 * AOV

    # Stream B: newly visible SKU on attribute demand
    rev_b_cons = (strong_m + attr_m * 0.3) * 0.12 * 0.025 * 0.14 * AOV
    rev_b_opt = (strong_m + attr_m * 0.5) * 0.25 * 0.035 * 0.16 * AOV

    base = rev_strong + rev_attr
    opt = rev_strong_opt + rev_attr_opt

    return {
        "aov": AOV,
        "matched_queries": len(hits),
        "freq_90d_total": freq_strong + freq_attr,
        "freq_90d_strong": freq_strong,
        "freq_90d_attr_phrase": freq_attr,
        "freq_90d_head": freq_strong,
        "freq_90d_tail": freq_attr,
        "stream_a_base_month": round(base),
        "stream_a_opt_month": round(opt),
        "stream_a_base_year": round(base * 12),
        "stream_a_opt_year": round(opt * 12),
        "stream_b_cons_month": round(rev_b_cons),
        "stream_b_opt_month": round(rev_b_opt),
        "text_stream_ref_month": 20804,
        "text_stream_ref_year": 249652,
        "assumptions": {
            "strong_uplift": "0.5 × (exact−fallback) on мельница/дойпак/hand-cooked…",
            "phrase_uplift_pp_base": 0.8,
            "phrase_uplift_pp_opt": 1.5,
            "order_exact": ORDER_EXACT,
            "order_fallback": ORDER_FALLBACK,
            "aov_source": "221 text-impact study 2026-06-21..2026-07-20",
            "match_rule": "distinctive tokens only; bare category nouns excluded",
        },
    }


def pick_cases(vision_rows: list[dict], n: int = 8) -> list[dict]:
    # diversify by attr
    by_attr: dict[str, list] = defaultdict(list)
    for r in vision_rows:
        by_attr[r["attribute_name"]].append(r)
    # load pictures from keep
    pics = {}
    if KEEP.exists():
        for r in json.loads(KEEP.read_text(encoding="utf-8")):
            pics[str(r.get("offer_id"))] = r.get("picture") or ""
    cases = []
    order = [
        "Форма выпуска",
        "Вкус, Добавки",
        "Тип упаковки",
        "Технология приготовления",
        "Нарезка",
        "Способ обработки",
        "Тип соуса",
        "Текстура корма",
    ]
    for an in order:
        for r in by_attr.get(an, [])[:1]:
            cases.append({**r, "picture": pics.get(r["external_id"], "")})
            if len(cases) >= n:
                return cases
    return cases


def fmt_rub(n: float | int) -> str:
    n = int(round(n))
    return f"{n:,}".replace(",", "\u202f") + "\u202f₽"


def build_html(payload: dict) -> str:
    keep_by = payload["keep_by_attr"]
    money = payload["money"]
    baseline = payload["baseline"]
    cases = payload["cases"]
    top_hits = payload["query_hits"][:25]
    skip = payload["skip_attrs"]

    case_html = []
    for i, c in enumerate(cases, 1):
        img = c.get("picture") or ""
        img_block = (
            f'<img src="{img}" alt="" loading="lazy"/>'
            if img
            else '<div class="noimg">нет фото</div>'
        )
        case_html.append(
            f"""
<div class="case">
  <div class="case-num">{i:02d}</div>
  <div class="case-img">{img_block}</div>
  <div>
    <div class="case-meta">{c.get('path') or c.get('product_type') or ''} · id {c['external_id']}</div>
    <h3>{c['offer_name']}</h3>
    <p class="case-line"><strong>{c['attribute_name']}</strong> = {c['attribute_value']}</p>
    <p class="case-meta">Источник: OCR/visual с упаковки · уже залито в Dashboard</p>
  </div>
</div>"""
        )

    hits_rows = "".join(
        f"<tr><td>{h['query']}</td><td class='num'>{h['frequency_90d']:,}</td>"
        f"<td>{', '.join(m['attribute_value'] for m in h['matches'][:3])}</td>"
        f"<td>{h['matches'][0]['attribute_name'] if h['matches'] else ''}</td></tr>"
        for h in top_hits
    )

    keep_rows = "".join(
        f"<tr><td>{k}</td><td class='num'>{v}</td><td>{payload['attr_why'].get(k,'')}</td></tr>"
        for k, v in keep_by
    )
    skip_rows = "".join(
        f"<tr><td>{r['name']}</td><td>{r['why']}</td></tr>" for r in skip
    )

    searches_90 = int(baseline.get("searches_90d") or 0)
    rev_search = float(baseline.get("revenue") or 0)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Азбука Вкуса — атрибуты с картинок: value для партнёра</title>
<style>
:root {{
  --bg:#f4f1ea; --ink:#1c1711; --muted:#6b5e52; --line:#ddd6cc;
  --card:#fff; --accent:#1f6f4a; --warn:#9a4a1a; --ok:#1f6f4a;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font:16px/1.5 "Segoe UI", system-ui, sans-serif; color:var(--ink); background:var(--bg); }}
.wrap {{ max-width:1100px; margin:0 auto; padding:36px 20px 90px; }}
h1 {{ font-size:30px; font-weight:700; letter-spacing:-0.02em; margin:0 0 10px; }}
h2 {{ font-size:21px; margin:42px 0 12px; color:var(--accent); }}
h3 {{ font-size:17px; margin:0 0 8px; }}
.lead {{ color:var(--muted); font-size:17px; max-width:760px; }}
.meta {{ margin:14px 0 26px; color:var(--muted); font-size:13px; }}
.tag {{ display:inline-block; background:#e7efe9; color:var(--accent); padding:3px 10px; font-size:12px; margin:0 6px 6px 0; border-radius:4px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:18px 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); padding:16px 14px; border-radius:8px; }}
.stat b {{ display:block; font-size:22px; font-weight:700; margin-bottom:4px; color:var(--accent); }}
.stat span {{ color:var(--muted); font-size:13px; }}
.callout {{ background:var(--card); border-left:4px solid var(--accent); padding:14px 16px; margin:18px 0; border-radius:0 8px 8px 0; }}
.callout.warn {{ border-left-color:var(--warn); }}
table {{ width:100%; border-collapse:collapse; background:var(--card); font-size:14px; }}
th, td {{ border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
th {{ background:#efeae3; font-weight:600; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
@media (max-width:800px) {{ .two {{ grid-template-columns:1fr; }} }}
.case {{ display:grid; grid-template-columns:48px 180px 1fr; gap:14px; background:var(--card); border:1px solid var(--line); padding:14px; margin:12px 0; border-radius:8px; }}
.case-num {{ font-size:20px; font-weight:700; color:var(--accent); }}
.case-img img {{ width:180px; height:180px; object-fit:contain; background:#faf8f5; display:block; }}
.noimg {{ width:180px; height:180px; background:#eee; display:flex; align-items:center; justify-content:center; color:#999; font-size:12px; }}
.case-meta {{ font-size:12px; color:var(--muted); margin-bottom:4px; }}
.case-line {{ margin:0 0 6px; }}
@media (max-width:800px) {{
  .case {{ grid-template-columns:1fr; }}
  .case-img img, .noimg {{ width:100%; height:auto; max-height:260px; }}
}}
footer {{ margin-top:48px; color:var(--muted); font-size:12px; }}
ul.tight li {{ margin:4px 0; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="tag">site_id 221 · Азбука Вкуса</div>
  <div class="tag">vision → Dashboard · залито</div>
  <div class="tag">+ оценка ₽</div>
  <h1>Атрибуты с картинок: что дали и сколько это стоит</h1>
  <p class="lead">
    После текстового gold по описаниям — отдельный vision-стрим с упаковок.
    На фото берём только <strong>позитивную поисковую лексику</strong> (форма выпуска, вкус-label, нарезка, технология).
    «Без X / не содержит» сознательно <strong>не льём</strong> — ломает поиск.
  </p>
  <p class="meta">
    Фид 66 259 SKU · vision-прогон {payload['vision_offers']} офферов (фокус-категории) ·
    OpenRouter <code>gemini-2.5-flash-lite</code> · заливка Dashboard {payload['keep_rows']} строк /
    {payload['keep_offers']} SKU · ClickHouse searches 90д · собрано {payload['generated_at']}
  </p>

  <div class="grid">
    <div class="stat"><b>{payload['keep_rows']:,}</b><span>строк атрибутов с картинок (залито)</span></div>
    <div class="stat"><b>{payload['keep_offers']:,}</b><span>SKU с новыми vision-attrs</span></div>
    <div class="stat"><b>{money['matched_queries']:,}</b><span>запросов с матчем к vision-значениям</span></div>
    <div class="stat"><b>{fmt_rub(money['stream_a_base_month'])}</b><span>стрим A · база Δ/мес (запросы)</span></div>
    <div class="stat"><b>{fmt_rub(money['stream_a_opt_month'])}</b><span>стрим A · оптимист Δ/мес</span></div>
    <div class="stat"><b>+{fmt_rub(money['stream_b_cons_month'])}…{fmt_rub(money['stream_b_opt_month'])}</b><span>стрим B · доп. потенциал / мес</span></div>
  </div>

  <div class="callout">
    <strong>Вывод для партнёра.</strong>
    Текст из описаний уже закрывает вкус/ноты/рекомендации (~47.7k SKU, оценка ~{fmt_rub(money['text_stream_ref_month'])}/мес).
    Vision даёт <em>другой</em> слой: то, что видно на этикетке и слабо лежит в тексте —
    «мельница», «дойпак», «hand cooked», «ломтики», вкус на пачке, которого нет в name.
    Вместе: база text + vision A <strong>{fmt_rub(money['text_stream_ref_month'] + money['stream_a_base_month'])}/мес</strong>,
    с upside B ещё <strong>+{fmt_rub(money['stream_b_cons_month'])}…{fmt_rub(money['stream_b_opt_month'])}</strong>.
  </div>
  <div class="callout warn">
    <strong>Два денежных слоя (как в методологии ЦУМ / Attr Enrichment).</strong><br/>
    <em>A — запросы:</em> уже идущий спрос, который лучше матчится после индексации attrs.<br/>
    <em>B — выдача:</em> доп. потенциал — SKU с новыми attrs чаще попадают в SERP по категорийному спросу.
    B сверху A, не вместо; полный A+B без оговорки завысит.
  </div>

  <h2>1. Что достали с картинок (KEEP → Dashboard)</h2>
  <table>
    <thead><tr><th>Атрибут</th><th>Строк</th><th>Зачем партнёру</th></tr></thead>
    <tbody>{keep_rows}</tbody>
  </table>

  <h2>2. С картинок доставать НЕ нужно</h2>
  <p class="lead" style="font-size:15px">Уже в описаниях / фиде / ломает поиск — в rejected log, не в индекс.</p>
  <table>
    <thead><tr><th>Класс</th><th>Почему skip</th></tr></thead>
    <tbody>{skip_rows}</tbody>
  </table>

  <h2>3. База партнёра (ClickHouse, 90 дней)</h2>
  <div class="grid">
    <div class="stat"><b>{searches_90:,}</b><span>поисков за 90 дней</span></div>
    <div class="stat"><b>{int(float(baseline.get('with_search') or 0)):,}</b><span>сессий с поиском</span></div>
    <div class="stat"><b>{fmt_rub(rev_search)}</b><span>выручка с заказами (90д, CH)</span></div>
    <div class="stat"><b>{fmt_rub(AOV)}</b><span>AOV (из partner study)</span></div>
  </div>

  <h2>4. Деньги: vision-стрим</h2>
  <div class="two">
    <div>
      <h3>Стрим A — запросы</h3>
      <table>
        <tr><th>Сценарий</th><th>₽/мес</th><th>₽/год</th></tr>
        <tr><td>Базовый (консерв.)</td><td class="num">{fmt_rub(money['stream_a_base_month'])}</td><td class="num">{fmt_rub(money['stream_a_base_year'])}</td></tr>
        <tr><td>Оптимистичный</td><td class="num">{fmt_rub(money['stream_a_opt_month'])}</td><td class="num">{fmt_rub(money['stream_a_opt_year'])}</td></tr>
      </table>
      <p class="meta">Матч (строгий): {money['matched_queries']} запросов · объём {money['freq_90d_total']:,} поисков / 90д
      (strong-сигналы {money.get('freq_90d_strong', money['freq_90d_head']):,} + phrase {money.get('freq_90d_attr_phrase', money['freq_90d_tail']):,}).
      Без head-nouns вроде «торт/молоко». Uplift: strong 50% от (exact−fallback={UPLIFT_FB*100:.2f} п.п.); phrase +0.8 п.п. AOV={AOV:,.0f} ₽.</p>
    </div>
    <div>
      <h3>Стрим B — доп. потенциал выдачи</h3>
      <table>
        <tr><th>Сценарий</th><th>₽/мес</th></tr>
        <tr><td>Conservative</td><td class="num">{fmt_rub(money['stream_b_cons_month'])}</td></tr>
        <tr><td>Optimistic</td><td class="num">{fmt_rub(money['stream_b_opt_month'])}</td></tr>
      </table>
      <p class="meta">Гипотеза catalog→SERP по хвосту спроса на vision-лексику. Не суммировать 1:1 с A.</p>
    </div>
  </div>

  <h2>5. Стек value: text + vision</h2>
  <table>
    <thead><tr><th>Стрим</th><th>Источник</th><th>₽/мес (база)</th><th>Статус</th></tr></thead>
    <tbody>
      <tr><td>Text gold</td><td>описания → custom attrs</td><td class="num">{fmt_rub(money['text_stream_ref_month'])}</td><td>изучено / к заливке</td></tr>
      <tr><td>Vision KEEP</td><td>упаковка → OCR/visual</td><td class="num">{fmt_rub(money['stream_a_base_month'])}</td><td><strong>залито в Dashboard</strong></td></tr>
      <tr><td><strong>Итого база</strong></td><td>text + vision A</td><td class="num"><strong>{fmt_rub(money['text_stream_ref_month'] + money['stream_a_base_month'])}</strong></td><td>без стрима B</td></tr>
      <tr><td>+ upside B</td><td>catalog visibility</td><td class="num">+{fmt_rub(money['stream_b_cons_month'])}…{fmt_rub(money['stream_b_opt_month'])}</td><td>опционально</td></tr>
    </tbody>
  </table>

  <h2>6. Запросы, которые цепляют vision-значения</h2>
  <table>
    <thead><tr><th>Запрос</th><th>Частота 90д</th><th>Совпавшие значения</th><th>Атрибут</th></tr></thead>
    <tbody>{hits_rows}</tbody>
  </table>

  <h2>7. Примеры с фото</h2>
  {''.join(case_html)}

  <h2>8. Что сделать дальше</h2>
  <ul class="tight">
    <li>Дождаться переиндексации feed-attribute / FIT после заливки vision.</li>
    <li>Не заливать негации из <code>221_azbuka_vision_rejected.csv</code>.</li>
    <li>Расширить vision на оставшуюся молочку/напитки (сейчас сэмпл) — там же packshot-uplift.</li>
    <li>Склеить с text-deck: партнёру одна история «описания + этикетка».</li>
  </ul>

  <footer>
    Методология: Attr Enrichment / MONEY_TWO_STREAMS_TEMPLATE · конверсия order из partner study 221
    (exact {ORDER_EXACT*100:.2f}% / fallback {ORDER_FALLBACK*100:.2f}%) ·
    файлы: <code>221_azbuka_vision_dashboard_upload.csv</code>, <code>vision_partner_money.json</code>
  </footer>
</div>
</body>
</html>
"""


def main():
    print("Loading vision CSV…")
    vision_rows = load_vision_rows()
    keep_by = Counter(r["attribute_name"] for r in vision_rows).most_common()
    offers = {r["external_id"] for r in vision_rows}
    summary = json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else {}

    print("CH baseline…")
    baseline = fetch_baseline()
    print(baseline)

    print("CH top queries…")
    queries = fetch_top_queries(20000)
    print("queries", len(queries))

    print("Matching…")
    hits = match_queries(queries, vision_rows)
    print("matched queries", len(hits), "freq", sum(h["frequency_90d"] for h in hits))

    money = money_from_matches(hits)
    cases = pick_cases(vision_rows)

    skip = [
        {
            "name": "Ноты аромата / вкус и послевкусие / характер вкуса",
            "why": "Уже массово в text gold (~1–2k строк на имя); с фото модель выдумывает",
        },
        {
            "name": "Рекомендации по применению / подаче",
            "why": "Текст описаний; на packshot обычно нет",
        },
        {
            "name": "КБЖУ, срок годности, температура хранения",
            "why": "Уже в YML params почти на всех SKU",
        },
        {
            "name": "Бренд / вес / страна / vendor",
            "why": "В name + params; коллизия с фидом",
        },
        {
            "name": "Апелласьон / регион / сорт винограда",
            "why": "Сильные params фида (тысячи заполнений)",
        },
        {
            "name": "Не содержит / без X / MSG-free / Non-GMO / БЗМЖ",
            "why": "Негация ломает поиск («сахар»→товар без сахара); rejected CSV",
        },
        {
            "name": "Тип обработки из описания (охлаждённый, сырокопчёный…)",
            "why": "Часто уже в text gold / name — не дублировать с фото",
        },
        {
            "name": "Product-only lifestyle (мясо на доске, торт на тарелке)",
            "why": "OCR=0; vision бесполезен",
        },
    ]

    attr_why = {
        "Форма выпуска": "Поиск «мельница», «пауч», форма фасовки — редко в тексте",
        "Вкус, Добавки": "Label на пачке, которого нет в name (напр. brownie)",
        "Тип упаковки": "Дойпак / стекло для специй — фильтруемый признак",
        "Технология приготовления": "Hand cooked и аналоги с этикетки",
        "Способ обработки": "Засахаренные / сушка — позитивный OCR",
        "Нарезка": "Ломтики / кусочки — визуал + этикетка",
        "Тип соуса": "Pet: в соусе / в желе с пауча",
        "Текстура корма": "Pet: филе / паштет с этикетки",
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site_id": 221,
        "keep_rows": len(vision_rows),
        "keep_offers": len(offers),
        "vision_offers": summary.get("offers_selected") or summary.get("offers_done_ok") or 5457,
        "keep_by_attr": keep_by,
        "attr_why": attr_why,
        "skip_attrs": skip,
        "baseline": baseline,
        "money": money,
        "query_hits": hits[:100],
        "cases": cases,
        "api_key": API_KEY,
    }

    (OUT / "vision_partner_money.json").write_text(
        json.dumps(
            {
                "money": money,
                "baseline": baseline,
                "keep_by_attr": keep_by,
                "matched_queries_top": hits[:50],
                "generated_at": payload["generated_at"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    html = build_html(payload)
    out_html = OUT / "221_azbuka_vision_partner.html"
    desk_html = DESK / "221_azbuka_vision_partner.html"
    out_html.write_text(html, encoding="utf-8")
    desk_html.write_text(html, encoding="utf-8")

    # zip package
    import zipfile

    zip_path = DESK / "221_azbuka_vision_partner.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(desk_html, "221_azbuka_vision_partner.html")
        z.write(OUT / "vision_partner_money.json", "vision_partner_money.json")
        z.write(CSV, "221_azbuka_vision_dashboard_upload.csv")
        rej = DESK / "221_azbuka_vision_rejected.csv"
        if rej.exists():
            z.write(rej, "221_azbuka_vision_rejected.csv")
        z.writestr(
            "README.md",
            "# Азбука Вкуса 221 — vision attrs partner pack\n\n"
            "- `221_azbuka_vision_partner.html` — преза для партнёра\n"
            "- `vision_partner_money.json` — расчёт ₽\n"
            "- `221_azbuka_vision_dashboard_upload.csv` — залитые строки\n"
            "- `221_azbuka_vision_rejected.csv` — специально НЕ льём\n",
        )

    print("HTML", desk_html)
    print("ZIP", zip_path)
    print(
        "A_base_month",
        money["stream_a_base_month"],
        "A_opt_month",
        money["stream_a_opt_month"],
        "B",
        money["stream_b_cons_month"],
        money["stream_b_opt_month"],
        "matched",
        money["matched_queries"],
        "freq90",
        money["freq_90d_total"],
    )


if __name__ == "__main__":
    main()
