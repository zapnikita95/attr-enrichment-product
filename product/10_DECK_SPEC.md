# 10. Спецификация HTML-deck (Petrovich QBR style)

## Референс

Визуальный и структурный образец: `petrovich_519_qbr_presentation.html`.

**Engine:**

- `decks/engine/qbr-deck.css` — стили (glass, accent #6366f1)
- `decks/engine/qbr-deck.js` — QBRDeck navigation + Chart.js helpers
- Chart.js 4.4.1 CDN
- `deck-data` JSON в `<script type="application/json" id="deck-data">`

---

## internal-defense.html (18 слайдов)

| # | tag | Тип | Контент |
|---|-----|-----|---------|
| 1 | Продукт | title-cover | «Обогащение каталога для поиска» |
| 2 | Проблема | big-list | 3 боли enterprise |
| 3 | Решение | grid2 | Текст + Vision стримы |
| 4 | Ценность | goal-card ×4 | zero↓, ndcg↑, Class E↑, new data |
| 5 | Процесс | flow-diagram | Studio → Extract → Dashboard |
| 6 | Метрики | slide-kpi | Усреднённые ориентиры + sparklines |
| 7 | Кейс | pattern-examples | Ювелирка: форма + metal |
| 8 | Кейс | slide-kpi + chart | Аптека: Class E/S/I/C |
| 9 | Кейс | pattern-examples | Fashion: OCR + принт |
| 10 | Кейс | metric-card | Text: 8858 / grocery |
| 11 | Studio | research-grid | Wizard 7 шагов |
| 12 | Архитектура | grid2 | 3 репо + порты |
| 13 | Enterprise | slide-attrs | Почему не PIM (Petrovich style) |
| 14 | Pricing | grid3 | 1×MRR + 5–10% |
| 15 | Процесс | work-grid | Фазы 0–9 |
| 16 | Сегменты | grid3 | Enterprise / Mid / New |
| 17 | Риски | big-list | Честные ограничения |
| 18 | План | slide-dark | Ask + next steps |

---

## client-overview.html (14 слайдов)

Упрощённая версия без внутренней кухни:

| # | Содержание |
|---|------------|
| 1 | Cover |
| 2 | Проблема |
| 3 | Решение (2 стрима) |
| 4 | Ценность (4 goal-cards) |
| 5 | Метрики портфолио |
| 6 | Кейс ювелирка |
| 7 | Кейс аптека |
| 8 | Кейс fashion |
| 9 | Как работает (Studio кратко) |
| 10 | Процесс для партнёра |
| 11 | Pricing |
| 12 | Пилот / next steps |
| 13 | CTA |
| 14 | Контакты (dark cover) |

---

## Элементы UI (из Petrovich)

| Элемент | CSS class | Использование |
|---------|-----------|---------------|
| Glass card | `.glass` | Все карточки контента |
| Goal KPI | `.goal-card` | 4 outcome на слайде ценности |
| Metric + sparkline | `.metric-card` `.sparkline` | KPI до/после |
| Insight | `.insight` `.insight.green` | Выводы для бизнеса |
| Rank list | `.rank-list` | Zero→result запросы |
| Attr audit | `.slide-attrs` `.attr-danger-tag` | Шумные атрибуты |
| Dark plan | `.slide-dark` `.plan-grid` | Roadmap / Ask |
| Nav | `.nav-dots` | Стрелки + dots |

---

## deck-data JSON schema (минимальный)

```json
{
  "meta": { "product": "", "partner": "" },
  "kpi": { "ndcg_at_20_delta": 0.003, "zero_reduction_pct": 33 },
  "sparklines": { "ndcg": [], "zero": [] },
  "serp_classes": { "before": {}, "after": {} },
  "zero_queries_closed": [],
  "lexicon": { "truly_new_sku_pct": 49 },
  "pricing": { "mrr": 0, "batch": 0, "recurring": 0 }
}
```

**Дефолт:** `decks/data/product-default.json`  
**Персонализация:** `tools/proposal_builder.py`

---

## proposal_builder.py

Генерирует `decks/generated/{partner}-proposal.html` из:

- `decks/templates/partner-proposal.template.html`
- Impact JSON (Studio)
- `portfolio/cases.yaml` (2–3 кейса по vertical)
- MRR → pricing block

---

## Технические требования

- Offline: relative paths к `engine/` или embedded CSS/JS
- Chart.js: `https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js`
- Навигация: Arrow keys, Space, Home/End
- Разрешение: оптимизировано под 1280×720 проектор

---

## Критерии приёмки deck

- [ ] Открывается локально (file:// или static server)
- [ ] Все слайды переключаются
- [ ] Графики рендерятся из deck-data
- [ ] Стиль совпадает с Petrovich (accent, glass, dark plan)

---

*Версия: 2026-Q3*
