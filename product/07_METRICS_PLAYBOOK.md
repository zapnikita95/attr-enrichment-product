# 07. Metrics Playbook

## Назначение

Инструкция для **анalyst**: где считать каждую метрику, когда фиксировать baseline, как упаковать в deck/QBR. Без этого playbook цифры на слайдах не verifiable.

**Owner:** Analyst (фазы 1, 2, 8). **Consumer:** Sales, PM, QBR deck.

---

## Общий timeline измерений

```
T0: baseline (до заливки) → T1: upload OK → T2: +2 нед индекс → T3: +4 нед QBR report
```

| Момент | Действия |
|--------|----------|
| T0 | NDCG baseline, zero% last month, SERP sample (optional) |
| T1 | Зафиксировать upload date, scope attrs |
| T2 | Первый sanity check NDCG |
| T3 | Full QBR deck, rank-list, Class E if available |

---

## NDCG@20

| Параметр | Значение |
|----------|----------|
| **Определение** | Normalized DCG@20 — качество ранжирования топ-20 |
| **Где считать** | Studio → `/api/ndcg` → `data/ndcg_store/{site_id}_latest.json` |
| **Когда** | Baseline до заливки + 2–4 недели после |
| **Как показать** | metric-card + sparkline «до X → после Y (+Z%)» |
| **Оговорка** | На высоком baseline приросты малы (+0.003), но положительны на объёме |

**Пошагово:**

1. Studio → выбрать site_id → Wizard / NDCG tab
2. Export `{site_id}_latest.json`
3. Поля: `ndcg_before`, `ndcg_after`, `delta`, monthly series для sparkline
4. В deck-data: `kpi.ndcg_at_20_delta`, `sparklines.ndcg[]`

**Пример формулировки слайда:**  
«NDCG@20 вырос с 0.847 до 0.850 (+0.003). На baseline enterprise даже малый delta = тысячи улучшенных сессий в месяц.»

---

## Нулевые запросы (zero%)

| Параметр | Значение |
|----------|----------|
| **Определение** | Доля поисковых запросов без результатов |
| **Где** | CH + Sort strategy `zero_queries`; Studio `zeros.monthly` |
| **Headline кейс** | Ювелирка: **−33%** |
| **Как показать** | Line chart по месяцам + rank-list |

**Rank-list шаблон (Petrovich #6 style):**

```
#  Запрос              Было      Стало
1  кольцо змея         842/мес   127 SKU
2  стельки ортопед.   1203/мес  89 SKU
3  футболка леопард    456/мес   234 SKU
```

**Пошагово:**

1. Studio impact JSON → `zero_to_nonzero[]` или CH export
2. Top-N по frequency
3. deck-data: `zero_queries_closed[]`, `kpi.zero_reduction_pct`

---

## Class E / S / I / C

| Параметр | Значение |
|----------|----------|
| **Определение** | SERP quality audit: Exact / Similar / Irrelevant / Complement |
| **Где** | Search quality eval (manual SERP audit) |
| **Как показать** | Bar chart до/после + insight row |

**Аптека (референсные цифры):**

| Class | До | После | Δ |
|-------|-----|-------|---|
| E (exact) | 41.2% | 43.8% | **+2.6pp** |
| S (similar) | — | — | −0.5pp |
| I (irrelevant) | 5.7% | 3.5% | **−2.2pp** |
| C (complement) | — | — | +0.1pp |

**Talk track:** «Class E +2.6pp = больше точных результатов; Class I −2.2pp = меньше "чай вместо стелек".»

deck-data: `serp_classes.before`, `serp_classes.after`

---

## Precision@20

- Использовать **вместе** с NDCG на слайде KPI (3 metric-cards)
- Аптека: **+0.010**
- Источник: post-impl eval, тот же audit что NDCG
- Не путать с Class E — precision техническая, Class E бизнес-язык

---

## Lexicon gap / coverage

| Параметр | Значение |
|----------|----------|
| **Где** | Studio Wizard steps 3–4 |
| **Метрики** | gap_pct, truly_new_sku_pct, closure forecast |
| **Как показать** | Doughnut «X% gap закроет CSV» |
| **Befree ref** | 49% truly_new lexicon |

**Pre-sales use:** показать **до** подписания — «вот сколько SKU получат новые слова в индексе».

---

## Product reach

| Параметр | Значение |
|----------|----------|
| **Где** | Studio `product_reach_rows` в impact JSON |
| **Как показать** | «Y SKU получат новую discoverability» |
| **Связь с ROI** | Больше reach → выше zero_to_nonzero potential |

---

## Шаблон слайда «До/после» (Petrovich #3)

```
┌─────────────────────────────────────────────────┐
│  [metric-card: ndcg] [precision] [zero%]        │
│  [sparklines under each]                        │
├─────────────────────────────────────────────────┤
│  insight green: «Zero −33% — headline для CEO»  │
│  insight green: «Class E +2.6pp — UX win»       │
│  insight purple: «Reach 80k SKU»                │
│  insight purple: «49% truly_new — fashion»      │
├─────────────────────────────────────────────────┤
│  foot: Studio + период 2026-Q1→Q2, site_id XXX  │
└─────────────────────────────────────────────────┘
```

---

## Чеклист перед QBR

- [ ] Baseline зафиксирован **до** заливки (дата в footnote)
- [ ] Период post-impl ≥ 2 недели (лучше 4)
- [ ] Источник указан на слайде (Studio / CH / SERP audit)
- [ ] Минимум 1 story-кейс с конкретным запросом
- [ ] Оговорка про baseline для малых delta ndcg
- [ ] zero rank-list ≥ 3 запросов (если есть data)
- [ ] Pricing block актуален (если upsell recurring)

---

## Связь с deck-data JSON

| Поле JSON | Метрика | Источник |
|-----------|---------|----------|
| `kpi.ndcg_at_20_delta` | NDCG | ndcg_store |
| `kpi.zero_reduction_pct` | Zero | CH / Studio |
| `kpi.precision_at_20_delta` | Precision | SERP eval |
| `serp_classes.before/after` | Class E/S/I/C | Manual audit |
| `zero_queries_closed[]` | Rank list | impact JSON |
| `lexicon.truly_new_sku_pct` | Lexicon | Studio step 4 |
| `partner_impact.product_reach_rows` | Reach | impact JSON |

**Дефолты:** [decks/data/product-default.json](../decks/data/product-default.json)  
**Персонализация:** [tools/proposal_builder.py](../tools/proposal_builder.py)

---

## Troubleshooting

| Проблема | Причина | Действие |
|----------|---------|----------|
| NDCG не изменился | Индекс не обновился / мало attrs | Check feed loader lag |
| Zero вырос | Seasonality | Compare YoY, same weekday |
| Class E flat | Мало audit sample | Increase SERP sample size |
| Studio JSON пустой | Incomplete wizard | Re-run steps 1–7 |

---

*Версия: 2026-Q3 · attr-enrichment-product*
