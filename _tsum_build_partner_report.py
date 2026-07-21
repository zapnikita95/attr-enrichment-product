# -*- coding: utf-8 -*-
"""Build partner-facing HTML research for TSUM image attributes (no pricing)."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"


def pct(n: float) -> str:
    return f"{n:.1f}%".replace(".0%", "%")


def num(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def main() -> None:
    inv = json.loads((OUT / "feed_inventory.json").read_text(encoding="utf-8"))
    gap = json.loads((OUT / "gap_analysis.json").read_text(encoding="utf-8"))
    dec = json.loads((OUT / "vision_attr_decision.json").read_text(encoding="utf-8"))
    impact = json.loads((OUT / "query_impact_refined.json").read_text(encoding="utf-8"))
    totals = json.loads((OUT / "ch_totals_90d.json").read_text(encoding="utf-8"))[0]
    keep = dec["keep"]
    direct = impact["tiers"]["direct_facet"]
    expanded = impact["tiers"]["expanded_style"]

    # Feed param table rows
    feed_rows = []
    for p in dec["feed_params"]:
        if p["role"] == "technical":
            continue
        feed_rows.append(
            f"<tr><td>{p['name']}</td><td>{p['fill_pct']}%</td>"
            f"<td>{', '.join(p['examples'][:3])}</td></tr>"
        )

    do_not = "".join(
        f"<tr><td>{x['attr']}</td><td>{x['why']}</td></tr>"
        for x in dec["do_not_extract_from_images"]
    )
    do_yes = "".join(
        f"<tr><td><strong>{x['attr']}</strong></td><td>{x['why']}</td></tr>"
        for x in dec["extract_from_images"]
    )

    fam_direct = "".join(
        f"<tr><td>{fam}</td><td>{num(st['searches_90d'])}</td><td>{st['queries']}</td>"
        f"<td>{', '.join(e['q'] for e in st['examples'][:3])}</td></tr>"
        for fam, st in sorted(
            direct["families"].items(), key=lambda x: -x[1]["searches_90d"]
        )
    )
    fam_exp = "".join(
        f"<tr><td>{fam}</td><td>{num(st['searches_90d'])}</td><td>{st['queries']}</td></tr>"
        for fam, st in sorted(
            expanded["families"].items(), key=lambda x: -x[1]["searches_90d"]
        )
    )

    examples = "".join(
        f"<tr><td>{r['bucket']}</td><td>{(r['product_name'] or '')[:48]}</td>"
        f"<td>{r['attr']}</td><td>{r['value']}</td><td>{r['evidence']}</td></tr>"
        for r in keep
        if r["canon"]
        in {
            "принт_узор",
            "силуэт_посадка",
            "воротник_вырез",
            "застежка",
            "капюшон",
            "силуэт_сумки",
            "фактура",
            "детали_декор",
        }
    )[:8000]  # truncate safety — rebuild properly
    # rebuild examples limited
    ex_rows = []
    for r in keep:
        if r["canon"] not in {
            "принт_узор",
            "силуэт_посадка",
            "воротник_вырез",
            "застежка",
            "капюшон",
            "силуэт_сумки",
            "фактура",
            "обувь_форма",
        }:
            continue
        ex_rows.append(
            f"<tr><td>{r['bucket']}</td><td>{(r['product_name'] or '')[:50]}</td>"
            f"<td>{r['attr']}</td><td>{r['value']}</td><td>{r['evidence']}</td></tr>"
        )
        if len(ex_rows) >= 24:
            break
    examples = "".join(ex_rows)

    top_cats = "".join(
        f"<tr><td>{c['name']}</td><td>{num(c['offers'])}</td><td>{c.get('url','')}</td></tr>"
        for c in (inv.get("top_categories_by_offers") or [])[:12]
    )

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>ЦУМ — атрибуты с картинок: исследование разрыва</title>
<style>
:root {{
  --bg:#f7f5f2; --ink:#1a1a1a; --muted:#5c5c5c; --line:#ddd6cc;
  --card:#fff; --accent:#1f3a2e; --warn:#7a3e1d; --ok:#1f3a2e;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font:16px/1.5 "Segoe UI", system-ui, sans-serif; color:var(--ink); background:var(--bg); }}
.wrap {{ max-width:1080px; margin:0 auto; padding:32px 20px 80px; }}
h1 {{ font-size:28px; font-weight:650; letter-spacing:-0.02em; margin:0 0 8px; }}
h2 {{ font-size:20px; margin:40px 0 12px; color:var(--accent); }}
h3 {{ font-size:16px; margin:24px 0 8px; }}
.lead {{ color:var(--muted); font-size:17px; max-width:720px; }}
.meta {{ margin:16px 0 28px; color:var(--muted); font-size:13px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin:20px 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); padding:16px 14px; }}
.stat b {{ display:block; font-size:22px; font-weight:650; margin-bottom:4px; }}
.stat span {{ color:var(--muted); font-size:13px; }}
.callout {{ background:var(--card); border-left:3px solid var(--accent); padding:14px 16px; margin:18px 0; }}
.callout.warn {{ border-left-color:var(--warn); }}
table {{ width:100%; border-collapse:collapse; background:var(--card); font-size:14px; }}
th, td {{ border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
th {{ background:#efeae3; font-weight:600; }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
@media (max-width:800px) {{ .two {{ grid-template-columns:1fr; }} }}
ul.tight li {{ margin:4px 0; }}
.tag {{ display:inline-block; background:#efeae3; padding:2px 8px; font-size:12px; margin-right:6px; }}
footer {{ margin-top:48px; color:var(--muted); font-size:12px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="tag">site_id 203 · Diginetica</div>
  <div class="tag">без прайсинга</div>
  <h1>ЦУМ: зачем нужны атрибуты с картинок</h1>
  <p class="lead">
    Исследование разрыва между поисковыми запросами, текущим YML-фидом и тем,
    что реально видно на фото. Цель — показать, <strong>какие атрибуты уже есть</strong>
    и <strong>какие нужно доставать с изображений</strong>, чтобы закрывать стилевые запросы
    (принт, силуэт, каблук, тип сумки, декор, парфюмерные ноты).
  </p>
  <p class="meta">
    Фид: tsum.xml от 2026-07-21 · {num(inv['offers_total'])} offer · ClickHouse sessions, 90 дней ·
    Vision-probe: OpenRouter <code>google/gemini-2.5-flash</code>, {dec['n_probed']} SKU
    (одежда, платья, обувь, сумки, парфюм, косметика, часы, украшения) · локальные модели не использовались.
  </p>

  <div class="grid">
    <div class="stat"><b>{num(inv['offers_total'])}</b><span>SKU в фиде, у всех есть picture</span></div>
    <div class="stat"><b>{inv['unique_param_names']}</b><span>уникальных имён param (из них часть — id)</span></div>
    <div class="stat"><b>{num(int(totals['searches']))}</b><span>поисков за 90 дней</span></div>
    <div class="stat"><b>{pct(float(totals['zero_pct']))}</b><span>zero-rate (частотный)</span></div>
    <div class="stat"><b>{num(direct['searches_90d'])}</b><span>прямых facet-запросов под vision-атрибуты</span></div>
    <div class="stat"><b>{num(expanded['searches_90d'])}</b><span>расширенный стиль (каблук/сумки/принт…)</span></div>
  </div>

  <div class="callout">
    <strong>Вывод для партнёра.</strong> Фид ЦУМа силён в «карточных» полях — бренд, цвет, материал, пол, размер.
    Слабое место — <em>визуальный стиль</em>, который покупатель формулирует в поиске и ждёт в фильтрах:
    принт, посадка, капюшон, застёжка, каблук, силуэт сумки, декор, OCR с флакона/циферблата.
    На пробе из 28 фото OpenRouter нашёл новые searchable-атрибуты у <strong>всех</strong> SKU;
    после фильтра коллизий с фидом — KEEP {dec['keep_count']} / REJECT {dec['reject_count']}.
  </div>

  <h2>1. Что уже есть в фиде</h2>
  <p class="lead" style="font-size:15px">Только человекочитаемые params (без brand_id / color_*_id / size_id и т.п.).</p>
  <table>
    <thead><tr><th>Параметр</th><th>Fill</th><th>Примеры</th></tr></thead>
    <tbody>{''.join(feed_rows)}</tbody>
  </table>

  <h2>2. С картинок выделять НЕ нужно</h2>
  <table>
    <thead><tr><th>Атрибут</th><th>Почему не берём с фото</th></tr></thead>
    <tbody>{do_not}</tbody>
  </table>

  <h2>3. С картинок выделять НУЖНО</h2>
  <table>
    <thead><tr><th>Атрибут</th><th>Почему это gap</th></tr></thead>
    <tbody>{do_yes}</tbody>
  </table>

  <h2>4. Поиск: на сколько запросов можно повлиять</h2>
  <p>
    Источник: ClickHouse <code>sessions.searches</code>, siteId=203, 90 дней.
    Всего <strong>{num(int(totals['searches']))}</strong> поисков,
    <strong>{num(int(totals['unique_queries']))}</strong> уникальных запросов.
    Топ-30k покрывает {num(gap['total_searches_in_top30k'])} поисков (~{pct(100*gap['total_searches_in_top30k']/max(int(totals['searches']),1))} объёма).
  </p>

  <div class="two">
    <div>
      <h3>Консервативно — прямые facet-формулировки</h3>
      <p>Запросы, которые буквально содержат недостающие facet-слова.</p>
      <div class="stat"><b>{num(direct['searches_90d'])}</b><span>{direct['unique_queries']} уникальных · {direct['share_top30k_pct']}% top-30k</span></div>
      <table>
        <thead><tr><th>Семейство</th><th>Поисков</th><th>Запросов</th><th>Примеры</th></tr></thead>
        <tbody>{fam_direct}</tbody>
      </table>
    </div>
    <div>
      <h3>Рабочая оценка — расширенный стиль</h3>
      <p>Каблук/платформа, типы сумок, принт, посадка, декор, парфюмерная лексика.</p>
      <div class="stat"><b>{num(expanded['searches_90d'])}</b><span>{expanded['unique_queries']} уникальных · {expanded['share_top30k_pct']}% top-30k</span></div>
      <table>
        <thead><tr><th>Семейство</th><th>Поисков</th><th>Запросов</th></tr></thead>
        <tbody>{fam_exp}</tbody>
      </table>
    </div>
  </div>

  <div class="callout warn">
    <strong>Важно про масштаб.</strong> Даже при брендовом поиске («Gucci», «Premiata») атрибуты с картинок
    работают как <em>фильтры и уточнение выдачи</em> — это не отражено полностью в facet-запросах выше.
    В фиде <code>attribute_details</code> заполнен только ~8%, <code>attribute_clasp</code> ~2%:
    визуальные детали есть на фото каталога ({num(inv['offers_with_picture'])} картинок), но не в индексе.
  </div>

  <h3>Token-gap (механика attributes_extraction)</h3>
  <p>
    Сопоставили токены top-30k запросов с корпусом name+params на выборке 80k offer
    (без id-полей и «Лого»-URL). Остаток (residual) — слова запроса, которых нет в индексируемом фиде:
  </p>
  <ul class="tight">
    <li>Поисков с residual: <strong>{num(gap['searches_with_residual'])}</strong> ({gap['residual_rate_searches_pct']}% top-30k)</li>
    <li>Часть residual — бренды/род («женские», транслит брендов) — это не vision</li>
    <li>Часть — стилевая лексика (каблук, картхолдер, вечернее, коктейльное, шлепки…) — как раз зона картинок + нормализации типов</li>
  </ul>

  <h2>5. Proof: OpenRouter vision на реальных фото ЦУМ</h2>
  <p>
    Модель смотрела только картинку + список уже известных params; просили не дублировать цвет/материал/бренд.
    Oversight: fashion KEEP подтверждён; единичные коллизии (концентрация уже в названии парфюма) отфильтрованы.
  </p>
  <table>
    <thead><tr><th>Категория</th><th>Товар</th><th>Атрибут</th><th>Значение</th><th>Evidence</th></tr></thead>
    <tbody>{examples}</tbody>
  </table>

  <h2>6. Приоритетные категории каталога</h2>
  <p>По объёму offer в фиде (и пересечению с тем, что ищут в CH — бренды + типы одежды/обуви/сумок):</p>
  <table>
    <thead><tr><th>Категория</th><th>Offers</th><th>URL</th></tr></thead>
    <tbody>{top_cats}</tbody>
  </table>
  <p>
    Для пилота рекомендуем порядок: <strong>женская одежда / платья → обувь → сумки → верхняя одежда → парфюм → часы</strong>.
    Там максимальная плотность стилевых запросов и визуально читаемые признаки.
  </p>

  <h2>7. Методология (коротко)</h2>
  <ol>
    <li>Инвентаризация YML (stream parse 1.5 GB) — params, fill, выборка по категориям.</li>
    <li>ClickHouse site 203 — топ-30k запросов / 90д + totals.</li>
    <li>Gap: токены запросов vs корпус фида (как lexicon/feed-collision в attributes_extraction).</li>
    <li>Vision-probe через OpenRouter (Gemini 2.5 Flash) — без локальных моделей.</li>
    <li>KEEP/REJECT: коллизия с фидом, негации, низкая search relevance.</li>
  </ol>

  <div class="callout">
    <strong>Что купить у нас (продуктово, без цены):</strong>
    пакет vision-атрибутов для поиска и фильтров —
    принт/узор, силуэт/посадка, капюшон, воротник/вырез, застёжка, декор/фактура,
    тип сумки, каблук/форма обуви, OCR парфюма и часов —
    с исключением дублей фида и заливкой в Dashboard feed attributes.
  </div>

  <footer>
    Артефакты: portfolio/tsum/ · feed_inventory.json · gap_analysis.json ·
    query_impact_refined.json · vision_probe_results.json · vision_attr_decision.json · VISION_ATTR_DECISION.md
  </footer>
</div>
</body>
</html>
"""
    path = OUT / "tsum-image-attrs-research.html"
    path.write_text(html, encoding="utf-8")
    print("Wrote", path)


if __name__ == "__main__":
    main()
