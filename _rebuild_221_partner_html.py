# -*- coding: utf-8 -*-
"""Partner-facing HTML for 221 Azbuka vision attrs (no other brands, no internal jargon)."""
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
TEXT_MONTH = 20804.0


def fmt_rub(x: float) -> str:
    return f"{int(round(x)):,}".replace(",", "\u202f") + "\u202f₽"


def fmt_int(x: int | float) -> str:
    return f"{int(round(x)):,}".replace(",", "\u202f")


def short_q(q: str, n: int = 48) -> str:
    q = (q or "").strip()
    return q if len(q) <= n else q[: n - 1] + "…"


def clean_examples(examples: str, limit: int = 3) -> str:
    parts = [short_q(p.strip(), 40) for p in (examples or "").split(",") if p.strip()]
    return ", ".join(parts[:limit]) if parts else "—"


# Partner-facing copy (no internal jargon)
WHY = {
    "Форма выпуска": "На упаковке видно форму фасовки (мельница, пауч, зёрна) — в названии товара этого часто нет",
    "Вкус, Добавки": "Вкус с этикетки, которого нет в названии (например, brownie, чили, трюфель)",
    "Тип упаковки": "Тип тары — удобный признак для фильтра и уточнения поиска",
    "Технология приготовления": "Пометки вроде Hand cooked прямо с этикетки",
    "Способ обработки": "Вяленые, сушёные, засахаренные — читаем с упаковки",
    "Нарезка": "Ломтики, кусочки, слайсы — по фото и этикетке",
    "Тип соуса": "Для кормов: «в соусе» / «в желе» с пауча",
    "Текстура корма": "Для кормов: филе, паштет, мусс с этикетки",
}

IMPACT = {
    "Форма выпуска": "Запросы по форме («кофе в зёрнах», «мельница», «пюре») точнее находят нужные товары",
    "Вкус, Добавки": "Длинный хвост вкусов («с трюфелем», «пармезан») лучше попадает в выдачу",
    "Тип упаковки": "Поиск «в стекле», «дойпак» начинает опираться на реальный признак товара",
    "Технология приготовления": "Редкие, но точные запросы вроде hand cooked получают матч",
    "Способ обработки": "«Вяленые томаты», «сушёное манго» — прямое попадание в карточку",
    "Нарезка": "«Сыр нарезка», «слайсы» — выдача ближе к ожиданию покупателя",
    "Тип соуса": "Уточнение по влажным кормам «в соусе / в желе»",
    "Текстура корма": "Уточнение по текстуре корма (паштет, филе)",
}


def extract_cases(html: str) -> str:
    cases = re.findall(r'<div class="case">.*?</div>\s*</div>', html, re.S)
    if not cases:
        return ""
    skip_if = (
        "Тип упаковки</strong> = пакет",
        "Текстура корма</strong> = crunchy",
        "Тип соуса</strong> = чили",  # sauce type on chili sauce is weak
    )
    out = []
    n = 0
    for block in cases:
        if any(s in block for s in skip_if):
            continue
        n += 1
        block = block.replace(
            "Источник: OCR/visual с упаковки · уже залито в Dashboard",
            "Считано с упаковки · уже в поиске",
        )
        block = re.sub(
            r'<div class="case-num">\d+</div>',
            f'<div class="case-num">{n:02d}</div>',
            block,
            count=1,
        )
        # hide internal id in meta line
        block = re.sub(r"\s·\s*id\s+\d+", "", block)
        out.append(block)
        if n >= 6:
            break
    return "\n".join(out)


def main() -> None:
    data = json.loads(FACET.read_text(encoding="utf-8"))
    families = sorted(data["facet_families"], key=lambda f: -f["searches_90d"])
    # drop near-zero pet rows from hero tables? keep but de-emphasize — partner should see honesty
    base = data["baseline_ch"]
    aov = float(data["aov"])
    stream_a = float(data["stream_a_month_sum"])
    stream_a_opt = stream_a * 1.9
    stream_b_lo = stream_a * 0.05
    stream_b_hi = stream_a * 0.15
    total_facet = sum(f["searches_90d"] for f in families)
    total_uniq = sum(f["unique_queries"] for f in families)
    keep_rows = sum(f["keep_rows"] for f in families)
    generated = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    old = OLD_HTML.read_text(encoding="utf-8") if OLD_HTML.exists() else ""
    cases = extract_cases(old)
    if not cases:
        cases = "<p class='meta'>Примеры карточек — в приложении к исследованию.</p>"

    form_s = next((f["searches_90d"] for f in families if f["attr"] == "Форма выпуска"), 0)

    summary_rows = "".join(
        f"<tr>"
        f"<td>{f['attr']}</td>"
        f"<td class='num'>{fmt_int(f['keep_rows'])}</td>"
        f"<td class='num'>{fmt_int(f['searches_90d'])}</td>"
        f"<td class='num'>{fmt_int(f['unique_queries'])}</td>"
        f"<td>{clean_examples(f['examples'])}</td>"
        f"<td class='num'>{fmt_rub(f['delta_rub_month'])}</td>"
        f"</tr>"
        for f in families
    )

    impact_rows = "".join(
        f"<tr>"
        f"<td><strong>{f['attr']}</strong></td>"
        f"<td>{IMPACT.get(f['attr'], f.get('impact', ''))}</td>"
        f"<td class='num'>{fmt_int(f['searches_90d'])}</td>"
        f"<td class='num'>{fmt_rub(f['delta_rub_month'])}</td>"
        f"<td>{WHY.get(f['attr'], f.get('why', ''))}</td>"
        f"</tr>"
        for f in families
    )

    detail_blocks = []
    for f in families:
        if f["searches_90d"] < 10 and f["attr"] in {"Тип соуса", "Текстура корма", "Технология приготовления"}:
            # compact one-liner for tiny demand
            ex = clean_examples(
                ", ".join(q["q"] for q in f["top_queries"][:3]),
                3,
            )
            detail_blocks.append(
                f"""
      <div class="fam compact">
        <h3>{f['attr']} · {fmt_int(f['searches_90d'])} поисков / 90 дней</h3>
        <p class="meta">{WHY.get(f['attr'], '')} Примеры: {ex}. Оценка ~{fmt_rub(f['delta_rub_month'])}/мес.</p>
      </div>"""
            )
            continue
        qrows = "".join(
            f"<tr><td>{short_q(q['q'], 64)}</td><td class='num'>{fmt_int(q['s'])}</td></tr>"
            for q in f["top_queries"][:8]
        )
        detail_blocks.append(
            f"""
      <div class="fam">
        <h3>{f['attr']} · {fmt_int(f['searches_90d'])} поисков · {fmt_int(f['unique_queries'])} формулировок</h3>
        <p class="meta">{WHY.get(f['attr'], '')} · {IMPACT.get(f['attr'], '')}</p>
        <table>
          <thead><tr><th>Запрос</th><th>Поисков за 90 дней</th></tr></thead>
          <tbody>{qrows}</tbody>
        </table>
      </div>"""
        )

    keep_rows_html = "".join(
        f"<tr><td>{f['attr']}</td><td class='num'>{fmt_int(f['keep_rows'])}</td>"
        f"<td>{WHY.get(f['attr'], '')}</td></tr>"
        for f in sorted(families, key=lambda x: -x["keep_rows"])
    )

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Азбука Вкуса — атрибуты с картинок товаров</title>
<style>
:root {{
  --bg:#f7f4ef; --ink:#1a1510; --muted:#6a5d52; --line:#d9d1c6;
  --card:#fff; --accent:#0f5c3c; --warn:#8a5a2b; --hi:#143d2a;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font:16px/1.55 "Segoe UI", system-ui, sans-serif; color:var(--ink); background:var(--bg); }}
.wrap {{ max-width:1080px; margin:0 auto; padding:40px 22px 96px; }}
h1 {{ font-size:28px; font-weight:700; letter-spacing:-0.02em; margin:0 0 12px; }}
h2 {{ font-size:20px; margin:40px 0 12px; color:var(--accent); }}
h3 {{ font-size:16px; margin:0 0 6px; color:var(--hi); }}
.lead {{ color:var(--muted); font-size:17px; max-width:780px; margin:0 0 8px; }}
.meta {{ margin:8px 0 16px; color:var(--muted); font-size:13px; }}
.tag {{ display:inline-block; background:#e4efe8; color:var(--accent); padding:3px 10px; font-size:12px; margin:0 6px 8px 0; border-radius:4px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:18px 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); padding:16px 14px; border-radius:8px; }}
.stat b {{ display:block; font-size:22px; font-weight:700; margin-bottom:4px; color:var(--accent); }}
.stat span {{ color:var(--muted); font-size:13px; }}
.callout {{ background:var(--card); border-left:4px solid var(--accent); padding:14px 16px; margin:18px 0; border-radius:0 8px 8px 0; }}
.callout.note {{ border-left-color:var(--warn); }}
table {{ width:100%; border-collapse:collapse; background:var(--card); font-size:14px; margin:10px 0 18px; }}
th, td {{ border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
th {{ background:#efeae3; font-weight:600; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.fam {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:14px 16px; margin:12px 0; }}
.fam.compact {{ padding:12px 14px; }}
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
footer {{ margin-top:48px; color:var(--muted); font-size:12px; line-height:1.45; }}
ul.tight li {{ margin:6px 0; }}
.hirow {{ background:#f0f7f3; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="tag">Азбука Вкуса · av.ru</div>
  <div class="tag">атрибуты с фото упаковки</div>
  <div class="tag">данные поиска · 90 дней</div>

  <h1>Атрибуты с картинок: спрос в поиске и эффект для выручки</h1>
  <p class="lead">
    С фото упаковки извлекли признаки, которых часто нет в названии товара:
    форма выпуска, вкус с этикетки, нарезка, способ обработки и др.
    Ниже — реальные запросы покупателей и оценка влияния на поиск.
  </p>
  <p class="meta">
    Каталог: 66 259 товаров · обработано фото: 5 457 · в поиск добавлено: {fmt_int(keep_rows)} значений
    на ~1 885 товарах · период анализа: 90 дней · дата: {generated}
  </p>

  <div class="grid">
    <div class="stat"><b>{fmt_int(total_facet)}</b><span>поисков по этим признакам / 90 дней</span></div>
    <div class="stat"><b>{fmt_int(total_uniq)}</b><span>разных формулировок запросов</span></div>
    <div class="stat"><b>{fmt_int(base.get('searches_90d') or 0)}</b><span>всех поисков на сайте / 90 дней</span></div>
    <div class="stat"><b>{fmt_rub(stream_a)}</b><span>оценка доп. выручки / мес (база)</span></div>
    <div class="stat"><b>{fmt_rub(stream_a_opt)}</b><span>оценка доп. выручки / мес (оптимист)</span></div>
    <div class="stat"><b>{fmt_rub(TEXT_MONTH + stream_a)}</b><span>вместе с атрибутами из описаний / мес</span></div>
  </div>

  <div class="callout">
    <strong>Вывод.</strong>
    Покупатели уже ищут то, что видно на упаковке, но слабо отражено в названии.
    За 90 дней — <strong>{fmt_int(total_facet)}</strong> таких запросов
    (больше всего — форма выпуска: {fmt_int(form_s)}).
    После добавления признаков в поиск эти запросы чаще находят нужный товар.
  </div>

  <h2>1. Какие признаки сколько ищут</h2>
  <p class="meta">
    Источник: поисковые запросы на сайте за 90 дней.
    Считаем прямые формулировки («мельница», «в зёрнах», «вяленые», «нарезка»…) —
    без общих слов вроде «масло» или «торт».
  </p>
  <table>
    <thead>
      <tr>
        <th>Признак</th>
        <th>Добавлено значений</th>
        <th>Поисков / 90 дн.</th>
        <th>Формулировок</th>
        <th>Примеры запросов</th>
        <th>Оценка ₽/мес</th>
      </tr>
    </thead>
    <tbody>{summary_rows}</tbody>
    <tfoot>
      <tr class="hirow">
        <td><strong>Итого</strong></td>
        <td class="num"><strong>{fmt_int(keep_rows)}</strong></td>
        <td class="num"><strong>{fmt_int(total_facet)}</strong></td>
        <td class="num"><strong>{fmt_int(total_uniq)}</strong></td>
        <td></td>
        <td class="num"><strong>{fmt_rub(stream_a)}</strong></td>
      </tr>
    </tfoot>
  </table>

  <h2>2. На что это влияет в поиске</h2>
  <table>
    <thead>
      <tr>
        <th>Признак</th>
        <th>Эффект для поиска</th>
        <th>Спрос / 90 дн.</th>
        <th>₽/мес</th>
        <th>Почему берём с фото</th>
      </tr>
    </thead>
    <tbody>{impact_rows}</tbody>
  </table>
  <p class="meta">
    Оценка: число релевантных поисков × ожидаемый прирост конверсии в заказ × средний чек
    ({fmt_rub(aov)}). Консервативный сценарий; оптимистичный — примерно в 1,9 раза выше.
  </p>

  <h2>3. База по сайту (90 дней)</h2>
  <div class="grid">
    <div class="stat"><b>{fmt_int(base.get('searches_90d') or 0)}</b><span>поисков</span></div>
    <div class="stat"><b>{fmt_int(base.get('with_search') or 0)}</b><span>сессий с поиском</span></div>
    <div class="stat"><b>{fmt_int(base.get('orders') or 0)}</b><span>заказов</span></div>
    <div class="stat"><b>{fmt_rub(float(base.get('revenue') or 0))}</b><span>выручка</span></div>
    <div class="stat"><b>{fmt_rub(aov)}</b><span>средний чек (AOV)</span></div>
  </div>
  <div class="callout note">
    <strong>Уточнение по Яндекс.Метрике.</strong>
    Сейчас оценка опирается на данные поиска Diginetica.
    Если откроете гостевой доступ к счётчику Яндекс.Метрики сайта — пересчитаем
    конверсию и средний чек по Метрике и обновим денежную оценку.
  </div>

  <h2>4. Примеры запросов по каждому признаку</h2>
  {''.join(detail_blocks)}

  <h2>5. Что добавили в поиск с фото</h2>
  <table>
    <thead><tr><th>Признак</th><th>Значений</th><th>Зачем</th></tr></thead>
    <tbody>{keep_rows_html}</tbody>
  </table>

  <h2>6. Что с фото не берём</h2>
  <table>
    <thead><tr><th>Тип данных</th><th>Почему не добавляем</th></tr></thead>
    <tbody>
      <tr><td>Ноты вкуса и аромата из описания</td><td>Уже закрываются разбором текстовых описаний</td></tr>
      <tr><td>КБЖУ, срок годности, температура хранения</td><td>Уже есть в карточке товара / фиде</td></tr>
      <tr><td>Бренд, вес, страна</td><td>Уже в названии и параметрах</td></tr>
      <tr><td>«Без сахара», «не содержит…», -free</td><td>Такие формулировки ухудшают поиск — сознательно не добавляем</td></tr>
      <tr><td>Апелласьон / сорт винограда</td><td>Уже заполнены в параметрах фида</td></tr>
    </tbody>
  </table>

  <h2>7. Оценка эффекта</h2>
  <div class="two">
    <div>
      <h3>По поисковым запросам</h3>
      <table>
        <tr><th>Сценарий</th><th>₽/мес</th><th>₽/год</th></tr>
        <tr><td>Базовый</td><td class="num">{fmt_rub(stream_a)}</td><td class="num">{fmt_rub(stream_a*12)}</td></tr>
        <tr><td>Оптимистичный</td><td class="num">{fmt_rub(stream_a_opt)}</td><td class="num">{fmt_rub(stream_a_opt*12)}</td></tr>
      </table>
    </div>
    <div>
      <h3>Вместе с атрибутами из описаний</h3>
      <table>
        <tr><th>Источник</th><th>₽/мес</th></tr>
        <tr><td>Из текстовых описаний</td><td class="num">{fmt_rub(TEXT_MONTH)}</td></tr>
        <tr><td>С фото упаковки</td><td class="num">{fmt_rub(stream_a)}</td></tr>
        <tr class="hirow"><td><strong>Итого (база)</strong></td><td class="num"><strong>{fmt_rub(TEXT_MONTH + stream_a)}</strong></td></tr>
        <tr><td>Доп. потенциал видимости в выдаче</td><td class="num">+{fmt_rub(stream_b_lo)}…{fmt_rub(stream_b_hi)}</td></tr>
      </table>
    </div>
  </div>

  <h2>8. Примеры товаров</h2>
  {cases}

  <h2>9. Следующие шаги</h2>
  <ul class="tight">
    <li>Дождаться полной переиндексации добавленных признаков в поиске.</li>
    <li>При желании уточнить денежную оценку — гостевой доступ к Яндекс.Метрике сайта.</li>
    <li>При необходимости расширить разбор фото на остальные категории с упаковкой.</li>
  </ul>

  <footer>
    Исследование для Азбуки Вкуса · атрибуты с фото упаковки · поиск за 90 дней · {generated}.
    Оценка выручки — модель на основе частоты запросов, прироста конверсии и среднего чека.
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
                "text_stream_ref_month": TEXT_MONTH,
                "facet_total_searches_90d": total_facet,
                "partner_facing": True,
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
        z.writestr(
            "README.md",
            "# Азбука Вкуса — атрибуты с фото\n\n"
            "Отдайте партнёру файл `221_azbuka_vision_partner.html`.\n",
        )

    print("HTML", desk_html)
    print("ZIP", zip_path)


if __name__ == "__main__":
    main()
