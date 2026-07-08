# 10. Спецификация HTML-deck (Petrovich QBR style)

## Назначение

Полная спецификация HTML-презентаций: структура слайдов, UI-компоненты, JSON schema, генерация персональных decks.  
**Референс:** `C:\Users\1\Downloads\petrovich_519_qbr_presentation.html`

---

## Engine (decks/engine/)

| Файл | Строк | Содержание |
|------|-------|------------|
| `qbr-deck.css` | ~270 | Glass cards, accent #6366f1, dark plan, responsive 1280×720 |
| `qbr-deck.js` | ~240 | QBRDeck class: nav, Chart.js init, keyboard |

**CDN:** Chart.js 4.4.1 — `https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js`

**Навигация:** ← → arrows, Space, Home/End, dots bottom nav.

---

## Что копируем из Petrovich

| Элемент Petrovich | CSS / JS | Адаптация продукта |
|-------------------|----------|-------------------|
| Палитра #eef1f8, #6366f1 | qbr-deck.css | Без изменений |
| Cover 1024×571 | `.title-cover` | «Обогащение каталога · {Partner}» |
| goal-card ×4 | `.goal-card` | zero↓, ndcg↑, Class E↑, lexicon |
| metric-card + sparkline | Chart.js line | До/после batch |
| insight-row | `.insight.green/purple` | Бизнес-выводы |
| rank-list | `.rank-list` | Zero→result queries |
| slide-attrs | `.attr-danger-tag` | Petrovich noise audit |
| slide-dark plan | `.slide-dark .plan-grid` | Ask + roadmap |
| deck-data JSON | `#deck-data` | proposal_builder inject |

---

## internal-defense.html (18 слайдов)

| # | tag | Тип | Контент | Speaker time |
|---|-----|-----|---------|--------------|
| 1 | Продукт | title-cover | «Обогащение каталога для поиска» | 1 min |
| 2 | Проблема | big-list | 3 боли enterprise | 4 min |
| 3 | Решение | grid2 | Текст + Vision + Studio | 3 min |
| 4 | Ценность | goal-card ×4 | KPI outcomes | 2 min |
| 5 | Процесс | flow-diagram | Studio → Extract → Dashboard | 2 min |
| 6 | Метрики | slide-kpi | Portfolio averages + sparklines | 2 min |
| 7 | Кейс | pattern-examples | Ювелирка: form + metal | 2 min |
| 8 | Кейс | slide-kpi + chart | Аптека: Class E/S/I/C | 2 min |
| 9 | Кейс | pattern-examples | Fashion: OCR + принт | 2 min |
| 10 | Кейс | metric-card | Text: 8858 / grocery | 2 min |
| 11 | Studio | research-grid | Wizard 7 шагов | 2 min |
| 12 | Архитектура | grid2 | 3 repo + ports | 2 min |
| 13 | Enterprise | slide-attrs | Почему не PIM (Petrovich) | 3 min |
| 14 | Pricing | grid3 | 1×MRR + 5–10% | 3 min |
| 15 | Процесс | work-grid | Фазы 0–9 | 2 min |
| 16 | Сегменты | grid3 | Enterprise / Mid / New | 2 min |
| 17 | Риски | big-list | Ограничения | 3 min |
| 18 | План | slide-dark | Ask + next steps | 5 min |

**Файл:** [decks/internal-defense.html](../decks/internal-defense.html)  
**Data:** [decks/data/product-default.json](../decks/data/product-default.json)

---

## client-overview.html (14 слайдов)

Клиентская версия — без внутренней кухни (ports, repos detail, risks internal).

| # | tag | Контент |
|---|-----|---------|
| 1 | Cover | «Обогащение каталога · {Partner optional}» |
| 2 | Проблема | 3 боли (коротко) |
| 3 | Решение | 2 стрима |
| 4 | Ценность | 4 goal-cards |
| 5 | Метрики | Portfolio proof |
| 6 | Кейс | Ювелирка |
| 7 | Кейс | Аптека |
| 8 | Кейс | Fashion |
| 9 | Как работает | Studio кратко (diagnostic free) |
| 10 | Процесс | Для партнёра: diagnose → batch → metrics |
| 11 | Pricing | 1×MRR + recurring |
| 12 | Пилот | Next steps, timeline |
| 13 | CTA | Бесплатная диагностика |
| 14 | Контакты | slide-dark cover |

**Файл:** [decks/client-overview.html](../decks/client-overview.html)

---

## partner-proposal.template.html (6 слайдов)

Генерируется `proposal_builder.py` — персональный мини-deck:

1. Cover — partner name, site_id  
2. Impact forecast — zero_to_nonzero, product_reach, lexicon  
3. Selected cases — из cases.yaml  
4. Metrics hint — ndcg/zero ranges  
5. Pricing — batch + recurring  
6. CTA — next steps  

**Output:** `decks/generated/{partner}-proposal.html`

---

## Элементы UI (CSS reference)

| Элемент | Class | Когда использовать |
|---------|-------|-------------------|
| Glass card | `.glass` | Любой контент-блок |
| Goal KPI | `.goal-card` | Slide 4 value |
| Metric + chart | `.metric-card`, `.sparkline` | KPI slide |
| Insight | `.insight`, `.insight.green` | Business takeaways |
| Rank list | `.rank-list` | Zero queries closed |
| Attr audit | `.slide-attrs`, `.attr-danger-tag` | Petrovich noise |
| Dark CTA | `.slide-dark`, `.plan-grid` | Ask / contacts |
| Nav | `.nav-dots`, `.nav-arrow` | All decks |

---

## deck-data JSON schema

```json
{
  "meta": {
    "product": "Обогащение каталога",
    "partner": "",
    "site_id": 0,
    "period": "2026-Q2"
  },
  "kpi": {
    "ndcg_at_20_delta": 0.003,
    "precision_at_20_delta": 0.01,
    "zero_reduction_pct": 33
  },
  "sparklines": {
    "ndcg": [0.84, 0.841, 0.843, 0.85],
    "zero": [12.1, 11.8, 10.2, 8.1]
  },
  "serp_classes": {
    "before": { "E": 41.2, "I": 5.7 },
    "after": { "E": 43.8, "I": 3.5 }
  },
  "zero_queries_closed": [
    { "query": "кольцо змея", "freq": 842, "sku": 127 }
  ],
  "lexicon": {
    "truly_new_sku_pct": 49,
    "closed_pct": 35
  },
  "pricing": {
    "mrr": 150000,
    "batch": 150000,
    "recurring_pct": 7.5,
    "recurring": 11250
  },
  "partner_impact": {
    "zero_to_nonzero_freq": 15000,
    "product_reach_rows": 80000,
    "lexicon_gap_closure_pct": 42
  },
  "cases_selected": ["pharmacy_vision", "jewelry_form"]
}
```

**Дефолт:** [decks/data/product-default.json](../decks/data/product-default.json)

---

## proposal_builder.py workflow

```powershell
py -3.13 tools/proposal_builder.py ^
  --partner "Ozerki" ^
  --site-id 6390 ^
  --mrr 150000 ^
  --vertical "Аптека" ^
  --new-per-week 400 ^
  --impact-json "path\to\impact.json" ^
  --output decks/generated/ozerki-proposal.html
```

**Steps:**

1. Load cases.yaml → pick 3 by vertical + slide_priority  
2. Load impact JSON (optional) → partner_impact block  
3. Compute pricing from MRR + new_per_week  
4. Merge into product-default.json structure  
5. Replace `{{PLACEHOLDERS}}` in template  
6. Embed `{{DECK_DATA_JSON}}` in `<script id="deck-data">`

---

## generate_decks.py (optional rebuild)

If HTML slides regenerated from spec:

```powershell
py -3.13 tools/generate_decks.py
```

Use when bulk-updating slide content from product-default.json.

---

## Технические требования

| Requirement | Status |
|-------------|--------|
| Offline file:// open | Relative paths to engine/ |
| Chart.js CDN | Required for sparklines |
| Keyboard nav | QBRDeck.js |
| 1280×720 projector | CSS optimized |
| No backend | Static HTML only |
| Petrovich visual parity | accent, glass, dark slide |

---

## Критерии приёмки deck

- [x] internal-defense.html — 18 `<section class="slide">`
- [x] client-overview.html — 14 slides
- [x] Opens locally file://
- [x] All slides switch via arrows/dots
- [x] Charts render from deck-data
- [x] Style matches Petrovich (accent #6366f1, glass)
- [x] proposal_builder generates without error

---

## Petrovich 15 → Product mapping (reference)

| Petrovich # | Product slide |
|-------------|---------------|
| 1 Cover | Product title |
| 2 Goals | Partner value 4 cards |
| 3 KPI | Metrics before/after |
| 4 Platforms | Text vs Vision |
| 5 Conversion | Class E/S/I/C |
| 6 Zero | Rank-list case |
| 7 Linguistics | Studio lexicon |
| 8 Categories | Verticals portfolio |
| 9 Photo search | Vision stream |
| 10 Q2 results | Portfolio done |
| 11 Quality pie | SERP eval |
| 12 Synonyms | Text stream |
| 13 Attr audit | Enterprise PIM slide |
| 14 Q3 plan | Commercial offer |
| 15 Team | CTA / diagnostics |

---

*Версия: 2026-Q3 · attr-enrichment-product*
