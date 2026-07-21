# -*- coding: utf-8 -*-
"""Rebuild 221 partner HTML: TSUM-style facet proofs + Metrika status + impact."""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "portfolio" / "221_azbuka"
DESK = Path(r"C:\Users\1\OneDrive\Desktop")
FACET = OUT / "vision_facet_demand.json"
OLD_HTML = OUT / "221_azbuka_vision_partner.html"
TEXT_MONTH = 20804.0  # from text-impact study


def fmt_rub(x: float) -> str:
    return f"{int(round(x)):,}".replace(",", "\u202f") + "\u202f₽"


def fmt_int(x: int | float) -> str:
    return f"{int(round(x)):,}".replace(",", "\u202f")


def extract_cases(html: str) -> str:
    m = re.search(
        r'(<h2>7\. Примеры с фото</h2>\s*)(.*?)(\s*<h2>8\.)',
        html,
        re.S,
    )
    if m:
        return m.group(2).strip()
    # fallback: any .case blocks
    cases = re.findall(r'<div class="case">.*?</div>\s*</div>', html, re.S)
    return "\n".join(cases[:8])


def main() -> None:
    data = json.loads(FACET.read_text(encoding="utf-8"))
    families = sorted(data["facet_families"], key=lambda f: -f["searches_90d"])
    base = data["baseline_ch"]
    aov = float(data["aov"])
    stream_a = float(data["stream_a_month_sum"])
    # optimistic ~1.9x like prior deck
    stream_a_opt = stream_a * 1.9
    stream_b_lo = stream_a * 0.05
    stream_b_hi = stream_a * 0.15
    total_facet_searches = sum(f["searches_90d"] for f in families)
    total_uniq = sum(f["unique_queries"] for f in families)
    keep_rows = sum(f["keep_rows"] for f in families)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")

    old = OLD_HTML.read_text(encoding="utf-8") if OLD_HTML.exists() else ""
    cases = extract_cases(old) or "<p class='meta'>см. CSV / batch keep</p>"

    facet_summary_rows = "".join(
        f"<tr>"
        f"<td>{f['attr']}</td>"
        f"<td class='num'>{fmt_int(f['keep_rows'])}</td>"
        f"<td class='num'>{fmt_int(f['searches_90d'])}</td>"
        f"<td class='num'>{fmt_int(f['unique_queries'])}</td>"
        f"<td>{f['examples']}</td>"
        f"<td class='num'>{fmt_rub(f['delta_rub_month'])}</td>"
        f"</tr>"
        for f in families
    )

    impact_rows = "".join(
        f"<tr>"
        f"<td><strong>{f['attr']}</strong></td>"
        f"<td>{f['impact']}</td>"
        f"<td class='num'>{fmt_int(f['searches_90d'])}</td>"
        f"<td class='num'>{fmt_rub(f['delta_rub_month'])}</td>"
        f"<td>{f['why']}</td>"
        f"</tr>"
        for f in families
    )

    detail_blocks = []
    for f in families:
        qrows = "".join(
            f"<tr><td>{q['q']}</td><td class='num'>{fmt_int(q['s'])}</td></tr>"
            for q in f["top_queries"][:8]
        )
        detail_blocks.append(
            f"""
      <div class="fam">
        <h3>{f['attr']} · {fmt_int(f['searches_90d'])} поисков / 90д · {fmt_int(f['unique_queries'])} формулировок</h3>
        <p class="meta">{f['why']} · <em>{f['impact']}</em> · залито строк: {fmt_int(f['keep_rows'])} · оценка ~{fmt_rub(f['delta_rub_month'])}/мес</p>
        <table>
          <thead><tr><th>Запрос (пример)</th><th>Поисков / 90д</th></tr></thead>
          <tbody>{qrows}</tbody>
        </table>
      </div>"""
        )

    keep_simple = "".join(
        f"<tr><td>{f['attr']}</td><td class='num'>{fmt_int(f['keep_rows'])}</td>"
        f"<td>{f['why']}</td></tr>"
        for f in sorted(families, key=lambda x: -x["keep_rows"])
    )

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Азбука Вкуса — атрибуты с картинок: спрос и value</title>
<style>
:root {{
  --bg:#f7f4ef; --ink:#1a1510; --muted:#6a5d52; --line:#d9d1c6;
  --card:#fff; --accent:#0f5c3c; --warn:#9a4a1a; --hi:#143d2a;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font:16px/1.5 "Segoe UI", system-ui, sans-serif; color:var(--ink); background:var(--bg); }}
.wrap {{ max-width:1120px; margin:0 auto; padding:36px 20px 90px; }}
h1 {{ font-size:30px; font-weight:700; letter-spacing:-0.02em; margin:0 0 10px; }}
h2 {{ font-size:22px; margin:44px 0 12px; color:var(--accent); border-bottom:2px solid #cfe0d5; padding-bottom:6px; }}
h3 {{ font-size:17px; margin:0 0 6px; color:var(--hi); }}
.lead {{ color:var(--muted); font-size:17px; max-width:820px; }}
.meta {{ margin:10px 0 18px; color:var(--muted); font-size:13px; }}
.tag {{ display:inline-block; background:#e4efe8; color:var(--accent); padding:3px 10px; font-size:12px; margin:0 6px 6px 0; border-radius:4px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:18px 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); padding:16px 14px; border-radius:8px; }}
.stat b {{ display:block; font-size:22px; font-weight:700; margin-bottom:4px; color:var(--accent); }}
.stat span {{ color:var(--muted); font-size:13px; }}
.callout {{ background:var(--card); border-left:4px solid var(--accent); padding:14px 16px; margin:18px 0; border-radius:0 8px 8px 0; }}
.callout.warn {{ border-left-color:var(--warn); }}
table {{ width:100%; border-collapse:collapse; background:var(--card); font-size:14px; margin:10px 0 18px; }}
th, td {{ border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
th {{ background:#efeae3; font-weight:600; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.fam {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:14px 16px; margin:14px 0; }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
@media (max-width:800px) {{ .two {{ grid-template-columns:1fr; }} }}
.case {{ display:grid; grid-template-columns:48px 180px 1fr; gap:14px; background:var(--card); border:1px solid var(--line); padding:14px; margin:12px 0; border-radius:8px; }}
.case-num {{ font-size:20px; font-weight:700; color:var(--accent); }}
.case-img img {{ width:180px; height:180px; object-fit:contain; background:#faf8f5; display:block; }}
.case-meta {{ font-size:12px; color:var(--muted); margin-bottom:4px; }}
.case-line {{ margin:0 0 6px; }}
@media (max-width:800px) {{
  .case {{ grid-template-columns:1fr; }}
  .case-img img {{ width:100%; height:auto; max-height:260px; }}
}}
footer {{ margin-top:48px; color:var(--muted); font-size:12px; }}
ul.tight li {{ margin:5px 0; }}
.hirow {{ background:#f0f7f3; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="tag">site_id 221 · Азбука Вкуса (av.ru)</div>
  <div class="tag">vision → Dashboard · залито</div>
  <div class="tag">как у ЦУМ: facet-спрос</div>
  <h1>Атрибуты с картинок: пруфы спроса и влияние на поиск</h1>
  <p class="lead">
    Не «красивые лейблы», а <strong>прямые facet-запросы</strong> из поиска Diginetica за 90 дней —
    сколько раз люди ищут форму выпуска, нарезку, hand cooked и т.д., и на какие ₽ это влияет после заливки.
  </p>
  <p class="meta">
    Фид 66 259 SKU · vision 5 457 офферов · залито {fmt_int(keep_rows)} строк /
    ~1 885 SKU · источник спроса: ClickHouse <code>sessions.searches</code> · собрано {generated}
  </p>

  <div class="grid">
    <div class="stat"><b>{fmt_int(total_facet_searches)}</b><span>прямых facet-поисков под vision-атрибуты / 90д</span></div>
    <div class="stat"><b>{fmt_int(total_uniq)}</b><span>уникальных формулировок</span></div>
    <div class="stat"><b>{fmt_int(base.get('searches_90d') or 0)}</b><span>всех поисков сайта / 90д</span></div>
    <div class="stat"><b>{fmt_rub(stream_a)}</b><span>стрим A · база Δ/мес (по facet-семьям)</span></div>
    <div class="stat"><b>{fmt_rub(stream_a_opt)}</b><span>стрим A · оптимист Δ/мес</span></div>
    <div class="stat"><b>{fmt_rub(TEXT_MONTH + stream_a)}</b><span>text gold + vision A / мес</span></div>
  </div>

  <div class="callout">
    <strong>Главный вывод.</strong>
    По поиску уже есть спрос на packshot-лексику: суммарно
    <strong>{fmt_int(total_facet_searches)}</strong> поисков / 90д по 8 KEEP-атрибутам
    (топ — форма выпуска {fmt_int(next(f['searches_90d'] for f in families if f['attr']=='Форма выпуска'))},
    вкус-label, нарезка, способ обработки).
    Vision заливает значения <em>с этикетки</em>, которых нет в name → эти запросы чаще получают точный матч.
  </div>

  <h2>1. Пруфы: какие атрибуты сколько ищут (как у ЦУМ)</h2>
  <p class="meta">
    Источник: ClickHouse Diginetica, siteId=221, 90 дней.
    Считаем <em>прямые facet-формулировки</em> (мельница, пауч, hand cooked, ломтики, вяленые…),
    не «масло» / «торт» как category head.
    Всего поисков сайта: <strong>{fmt_int(base.get('searches_90d') or 0)}</strong>;
    top-50k запросов покрывают {fmt_int(data['query_universe']['volume_top50k'])}.
  </p>
  <table>
    <thead>
      <tr>
        <th>Атрибут (KEEP)</th>
        <th>Строк залито</th>
        <th>Поисков / 90д</th>
        <th>Уник. запросов</th>
        <th>Примеры запросов</th>
        <th>Δ ₽/мес (база)</th>
      </tr>
    </thead>
    <tbody>{facet_summary_rows}</tbody>
    <tfoot>
      <tr class="hirow">
        <td><strong>Итого facet</strong></td>
        <td class="num"><strong>{fmt_int(keep_rows)}</strong></td>
        <td class="num"><strong>{fmt_int(total_facet_searches)}</strong></td>
        <td class="num"><strong>{fmt_int(total_uniq)}</strong></td>
        <td></td>
        <td class="num"><strong>{fmt_rub(stream_a)}</strong></td>
      </tr>
    </tfoot>
  </table>

  <h2>2. Что именно повлияет на поиск (attr → эффект)</h2>
  <table>
    <thead>
      <tr>
        <th>Атрибут</th>
        <th>На что влияет в поиске</th>
        <th>Спрос / 90д</th>
        <th>Δ ₽/мес</th>
        <th>Почему с картинки</th>
      </tr>
    </thead>
    <tbody>{impact_rows}</tbody>
  </table>
  <div class="callout warn">
    <strong>Формула стрима A (как ЦУМ, но без Метрики CVR):</strong>
    Δ = searches_facet × uplift × AOV.
    Strong-сигналы (форма/нарезка/обработка): uplift ≈ 1.17 п.п. (½ от exact−fallback Digi study).
    Вкус-label: uplift ≈ 0.2 п.п. (phrase × 25% attribution).
    AOV = {fmt_rub(aov)} из partner text-impact study 221.
  </div>

  <h2>3. База партнёра — Яндекс.Метрика</h2>
  <div class="callout warn">
    <strong>Метрика Diginetica для av.ru недоступна.</strong><br/>
    {data['metrika']['note']}<br/><br/>
    Сайт отдаёт HTTP 450 на наш fetch (счётчик со страницы не снять).
    У ЦУМ был counter <code>21801616</code> в OAuth Digi — у Азбуки такого нет.
    <em>Нужен guest-доступ партнёра к счётчику Метрики</em> — тогда пересчитаем CVR/AOV/ecommerce 1:1 как в презе ЦУМ.
  </div>
  <p class="meta">Ниже — proxy-база из Diginetica ClickHouse (тот же период 90д), пока Метрики нет:</p>
  <div class="grid">
    <div class="stat"><b>{fmt_int(base.get('searches_90d') or 0)}</b><span>поисков / 90д (CH)</span></div>
    <div class="stat"><b>{fmt_int(base.get('with_search') or 0)}</b><span>сессий с поиском</span></div>
    <div class="stat"><b>{fmt_int(base.get('orders') or 0)}</b><span>заказов (withOrder)</span></div>
    <div class="stat"><b>{fmt_rub(float(base.get('revenue') or 0))}</b><span>выручка / 90д (CH)</span></div>
    <div class="stat"><b>{fmt_rub(aov)}</b><span>AOV (partner study)</span></div>
    <div class="stat"><b>—</b><span>CVR Метрики: нет доступа</span></div>
  </div>

  <h2>4. Разбор по атрибутам: запросы с частотами</h2>
  {''.join(detail_blocks)}

  <h2>5. Что достали с картинок (KEEP → Dashboard)</h2>
  <table>
    <thead><tr><th>Атрибут</th><th>Строк</th><th>Зачем</th></tr></thead>
    <tbody>{keep_simple}</tbody>
  </table>

  <h2>6. С картинок доставать НЕ нужно</h2>
  <table>
    <thead><tr><th>Класс</th><th>Почему skip</th></tr></thead>
    <tbody>
      <tr><td>Ноты аромата / вкус и послевкусие</td><td>Уже в text gold; с фото модель выдумывает</td></tr>
      <tr><td>КБЖУ, срок, температура</td><td>Уже в YML params</td></tr>
      <tr><td>Бренд / вес / страна</td><td>Коллизия с фидом</td></tr>
      <tr><td>Не содержит / без X / -free</td><td>Негация ломает поиск — только rejected CSV</td></tr>
      <tr><td>Вино: апелласьон / сорт</td><td>Сильные params фида</td></tr>
    </tbody>
  </table>

  <h2>7. Деньги: vision + text</h2>
  <div class="two">
    <div>
      <h3>Стрим A — facet-запросы</h3>
      <table>
        <tr><th>Сценарий</th><th>₽/мес</th><th>₽/год</th></tr>
        <tr><td>Базовый (facet families)</td><td class="num">{fmt_rub(stream_a)}</td><td class="num">{fmt_rub(stream_a*12)}</td></tr>
        <tr><td>Оптимистичный (~1.9×)</td><td class="num">{fmt_rub(stream_a_opt)}</td><td class="num">{fmt_rub(stream_a_opt*12)}</td></tr>
      </table>
    </div>
    <div>
      <h3>Стек</h3>
      <table>
        <tr><th>Стрим</th><th>₽/мес</th></tr>
        <tr><td>Text gold</td><td class="num">{fmt_rub(TEXT_MONTH)}</td></tr>
        <tr><td>Vision KEEP (A)</td><td class="num">{fmt_rub(stream_a)}</td></tr>
        <tr class="hirow"><td><strong>Итого база</strong></td><td class="num"><strong>{fmt_rub(TEXT_MONTH + stream_a)}</strong></td></tr>
        <tr><td>+ upside B (выдача)</td><td class="num">+{fmt_rub(stream_b_lo)}…{fmt_rub(stream_b_hi)}</td></tr>
      </table>
    </div>
  </div>

  <h2>8. Примеры с фото</h2>
  {cases}

  <h2>9. Что нужно от партнёра</h2>
  <ul class="tight">
    <li><strong>Доступ к Яндекс.Метрике av.ru</strong> (guest / представитель) — пересчитать §3 и CVR как у ЦУМ.</li>
    <li>Дождаться переиндексации feed-attribute после заливки vision.</li>
    <li>Не заливать негации из <code>221_azbuka_vision_rejected.csv</code>.</li>
  </ul>

  <footer>
    Пруфы запросов: Diginetica ClickHouse site 221 · 90д · facet families в
    <code>vision_facet_demand.json</code>.
    Метрика: недоступна Digi (has_metrika=false). Методология денег: MONEY_TWO_STREAMS + uplift из partner study 221.
  </footer>
</div>
</body>
</html>
"""

    out_html = OUT / "221_azbuka_vision_partner.html"
    desk_html = DESK / "221_azbuka_vision_partner.html"
    out_html.write_text(html, encoding="utf-8")
    desk_html.write_text(html, encoding="utf-8")

    money_path = OUT / "vision_partner_money.json"
    money_path.write_text(
        json.dumps(
            {
                "generated_at": generated,
                "stream_a_base_month": stream_a,
                "stream_a_opt_month": stream_a_opt,
                "stream_b_cons_month": stream_b_lo,
                "stream_b_opt_month": stream_b_hi,
                "text_stream_ref_month": TEXT_MONTH,
                "facet_total_searches_90d": total_facet_searches,
                "metrika_available": False,
                "source": "vision_facet_demand.json",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    zip_path = DESK / "221_azbuka_vision_partner.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(desk_html, "221_azbuka_vision_partner.html")
        z.write(FACET, "vision_facet_demand.json")
        z.write(money_path, "vision_partner_money.json")
        csv = DESK / "221_azbuka_vision_dashboard_upload.csv"
        if csv.exists():
            z.write(csv, "221_azbuka_vision_dashboard_upload.csv")
        rej = DESK / "221_azbuka_vision_rejected.csv"
        if rej.exists():
            z.write(rej, "221_azbuka_vision_rejected.csv")
        z.writestr(
            "README.md",
            "# Азбука 221 — vision partner pack (v2 facet proofs)\n\n"
            "- HTML: пруфы спроса по атрибутам + impact\n"
            "- vision_facet_demand.json: частоты запросов CH 90д\n"
            "- Метрика Digi: нет доступа — нужен guest от партнёра\n",
        )

    print("HTML", desk_html)
    print("ZIP", zip_path)
    print("stream_a", stream_a, "facet_searches", total_facet_searches)


if __name__ == "__main__":
    main()
