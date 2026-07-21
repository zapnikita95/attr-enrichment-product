# -*- coding: utf-8 -*-
"""Inject 5 visual demo cases + Metrika CVR into partner HTML; save reusable template snippet."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "portfolio" / "tsum"
HTML = OUT / "tsum-image-attrs-research.html"
CASES = OUT / "demo_cases.json"
METRIKA = OUT / "metrika_cvr.json"
MONEY = OUT / "money_impact.json"
TEMPLATE = OUT / "PARTNER_DEMO_CASES_TEMPLATE.md"


def case_card(c: dict, i: int) -> str:
    attrs = "".join(
        f"<li><strong>{a.get('name')}</strong>: {a.get('value')} "
        f"<span class='ev'>({a.get('evidence') or 'visual'})</span></li>"
        for a in (c.get("extracted_new") or [])[:6]
    )
    feed = c.get("feed_had") or {}
    feed_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in list(feed.items())[:8]
    )
    pic = c.get("picture") or ""
    url = c.get("url") or "#"
    return f"""
    <article class="case">
      <div class="case-num">{i}</div>
      <a class="case-img" href="{url}" target="_blank" rel="noopener">
        <img src="{pic}" alt="{c.get('name') or ''}" loading="lazy"/>
      </a>
      <div class="case-body">
        <div class="case-meta">{c.get('bucket')} · {c.get('vendor') or ''} · id {c.get('offer_id')}</div>
        <h3>{c.get('name')}</h3>
        <p class="case-line">{c.get('partner_one_liner')}</p>
        <div class="case-cols">
          <div>
            <h4>Уже было в фиде</h4>
            <table class="mini"><tbody>{feed_rows or '<tr><td colspan=2>—</td></tr>'}</tbody></table>
          </div>
          <div>
            <h4>Достали с картинки (не было в фиде)</h4>
            <ul class="attrs">{attrs}</ul>
          </div>
        </div>
      </div>
    </article>
    """


def main() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    metrika = json.loads(METRIKA.read_text(encoding="utf-8")) if METRIKA.exists() else {}
    money = json.loads(MONEY.read_text(encoding="utf-8")) if MONEY.exists() else {}

    html = HTML.read_text(encoding="utf-8")
    if ".case {" not in html:
        html = html.replace(
            "footer { margin-top:48px; color:var(--muted); font-size:12px; }",
            """footer { margin-top:48px; color:var(--muted); font-size:12px; }
.case { display:grid; grid-template-columns:56px 200px 1fr; gap:16px; background:var(--card); border:1px solid var(--line); padding:16px; margin:14px 0; align-items:start; }
.case-num { font-size:22px; font-weight:700; color:var(--accent); }
.case-img img { width:200px; height:200px; object-fit:cover; display:block; background:#eee; }
.case-meta { font-size:12px; color:var(--muted); margin-bottom:4px; }
.case-body h3 { margin:0 0 8px; font-size:17px; }
.case-line { margin:0 0 12px; font-size:14px; }
.case-cols { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.case-cols h4 { margin:0 0 6px; font-size:13px; color:var(--muted); font-weight:600; }
table.mini { font-size:12px; }
.attrs { margin:0; padding-left:18px; font-size:14px; }
.attrs .ev { color:var(--muted); font-size:12px; }
@media (max-width:800px) {
  .case { grid-template-columns:1fr; }
  .case-img img { width:100%; height:auto; max-height:280px; }
  .case-cols { grid-template-columns:1fr; }
}
""",
        )

    cards = "\n".join(case_card(c, i) for i, c in enumerate(cases, 1))
    mo = metrika.get("overall") or {}
    seg = (metrika.get("segment_params_search") or {}).get("with_search") or {}
    seg_wo = (metrika.get("segment_params_search") or {}).get("without_search") or {}
    base_mo = ((money.get("scenarios") or {}).get("base") or {}).get("calc", {}).get("revenue_month", {})

    metrika_block = f"""
  <h2>5. Наглядные кейсы: фото → атрибут (чего не было в фиде)</h2>
  <p class="lead" style="font-size:15px">
    Пять реальных карточек ЦУМ. Слева — что уже лежит в YML, справа — что vision взял с картинки.
    Модель: OpenRouter <code>google/gemini-2.5-flash</code>.
  </p>
  {cards}

  <h2>6. Конверсия из Яндекс.Метрики (не CH)</h2>
  <p class="meta">Счётчик {metrika.get('counter_id')} · период { (metrika.get('period') or {}).get('date1') } — { (metrika.get('period') or {}).get('date2') }</p>
  <div class="grid">
    <div class="stat"><b>{(mo.get('cvr_pct') if mo.get('cvr_pct') is not None else '—')}</b><span>CVR сайта (ecommerce / visits), %</span></div>
    <div class="stat"><b>{(f"{mo.get('aov'):,.0f}" if mo.get('aov') else '—')} ₽</b><span>средний чек (Метрика)</span></div>
    <div class="stat"><b>{(f"{mo.get('purchases'):,.0f}" if mo.get('purchases') else '—')}</b><span>покупок ecommerce / 90д</span></div>
    <div class="stat"><b>{(seg.get('cvr_pct') if seg.get('cvr_pct') is not None else '—')}</b><span>CVR визитов с params=search, %</span></div>
    <div class="stat"><b>{(seg_wo.get('cvr_pct') if seg_wo.get('cvr_pct') is not None else '—')}</b><span>CVR без params=search, %</span></div>
    <div class="stat"><b>{(f"{base_mo.get('total'):,}" if base_mo.get('total') else '—')} ₽</b><span>Δ выручка / мес (базовый, после пересчёта)</span></div>
  </div>
  <div class="callout warn">
    В Diginetica CH search-атрибуция заказов занижена (~0.08% CVR).
    Для партнёрской оценки денег используем Метрику (ecommerce) + API reserve/normal.
  </div>
"""

    # Remove old "5. Proof" section content replacement - insert before money or replace proof
    marker = "<h2>5. Proof: OpenRouter vision"
    if marker in html:
        # cut from marker until h2 6 or 7
        start = html.index(marker)
        # find next major h2 after proof - was "6. Приоритетные"
        nxt = html.find("<h2>6. Приоритетные", start)
        if nxt == -1:
            nxt = html.find("<h2>7. Деньги", start)
        if nxt != -1:
            html = html[:start] + metrika_block + "\n" + html[nxt:]
            # renumber following sections lightly - optional
    else:
        # insert before money section
        money_h = "<h2>7. Деньги:"
        if money_h in html:
            html = html.replace(money_h, metrika_block + "\n  " + money_h)
        else:
            html = html.replace("<h2>8. Методология", metrika_block + "\n  <h2>8. Методология")

    # Fix section numbers in rest if needed
    html = html.replace("<h2>6. Приоритетные категории", "<h2>7. Приоритетные категории")
    html = html.replace("<h2>7. Деньги:", "<h2>8. Деньги:")
    html = html.replace("<h2>8. Методология", "<h2>9. Методология")

    HTML.write_text(html, encoding="utf-8")

    TEMPLATE.write_text(
        """# Шаблон: наглядные кейсы атрибутов с картинок (для партнёра)

Всегда класть в HTML-отчёт блок **5 кейсов** (не таблицу без фото).

## Обязательные поля кейса

| Поле | Зачем |
|------|--------|
| `picture` | Крупное фото товара (CDN URL) |
| `name` / `offer_id` / `url` | Идентификация |
| `feed_had` | Что уже было в YML (name/params) — коротко |
| `extracted_new` | Атрибут + значение + evidence (visual/ocr) |
| `partner_one_liner` | 1 фраза: чего не было в фиде и что достали |

## Критерии отбора

1. Атрибут **реально новый** vs name+params (feed collision).
2. Разные категории (одежда / обувь / сумка / верхняя / …).
3. Желательно пересечение с поисковой лексикой (принт, каблук, капюшон…).
4. Не показывать негации и маркетинг («эффект: комфорт») как главный proof.

## Артефакты пайплайна

- `demo_cases.json` — данные кейсов
- `_tsum_pick_demo_cases.py` — отбор
- HTML-секция генерируется `_tsum_build_demo_html.py`

## Для нового партнёра

1. Vision probe → KEEP/REJECT
2. Выбрать 5 offer_id вручную или PREFERRED
3. Собрать `demo_cases.json`
4. Вставить в partner HTML **до** блока денег
""",
        encoding="utf-8",
    )
    print("Wrote HTML cases", len(cases), "template", TEMPLATE)


if __name__ == "__main__":
    main()
