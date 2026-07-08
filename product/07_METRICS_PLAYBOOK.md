# 07. Metrics Playbook

## Назначение

Инструкция для аналитика: **где считать**, **когда**, **как показывать** каждую метрику в deck и QBR.

---

## NDCG@20

| Параметр | Значение |
|----------|----------|
| **Где** | Studio → `/api/ndcg` → `data/ndcg_store/{site_id}_latest.json` |
| **Когда** | Baseline до заливки + 2–4 недели после |
| **Как показать** | Sparkline + «до X → после Y (+Z%)» |
| **Оговорка** | На высоком baseline приросты малы (+0.003), но положительны и статистически значимы на объёме |

**Пример слайда:** metric-card с value `+0.003` и sparkline из `deck-data.kpi`.

---

## Нулевые запросы (zero%)

| Параметр | Значение |
|----------|----------|
| **Где** | CH + Sort strategy `zero_queries`; Studio `zeros.monthly` |
| **Как показать** | Линейный график по месяцам + rank-list «запросы, ушедшие из нулей» |
| **Headline** | Ювелирка: **−33%** |

**Шаблон rank-list:**

```
1. кольцо змея        842 /мес  → 127 SKU
2. стельки ортопед.  1203 /мес → 89 SKU
```

---

## Class E / S / I / C

| Параметр | Значение |
|----------|----------|
| **Где** | Search quality eval (SERP audit) |
| **Как показать** | Bar chart до/после + insight «Class E +2.6pp = больше точных результатов» |

**Аптека (референс):**

| Class | До | После | Δ |
|-------|-----|-------|---|
| E (exact) | 41.2% | 43.8% | +2.6pp |
| I (irrelevant) | 5.7% | 3.5% | −2.2pp |

---

## Precision@20

- Использовать вместе с NDCG на слайде KPI.
- Аптека: **+0.010** — хороший якорь для «больше релевантных в топ-20».

---

## Lexicon gap / coverage

| Параметр | Значение |
|----------|----------|
| **Где** | Studio Wizard steps 3–4 |
| **Как показать** | Doughnut: «X% gap закроет планируемый CSV» |
| **Befree** | 49% truly_new lexicon |

---

## Product reach

| Параметр | Значение |
|----------|----------|
| **Где** | Studio `product_reach_rows` в impact JSON |
| **Как показать** | «Y SKU получат новую discoverability» |

---

## Шаблон слайда «До/после» (Petrovich #3 style)

```
[3 metric-cards: ndcg | precision | zero%]
[sparklines под каждой]
[insight-row: 4 вывода — 2 зелёных, 2 фиолетовых]
[foot: источник + период измерения]
```

---

## Чеклист перед QBR

- [ ] Baseline зафиксирован до заливки
- [ ] Период post-impl ≥ 2 недели
- [ ] Источник данных указан на слайде (Studio / CH / SERP audit)
- [ ] Есть минимум 1 story-кейс с запросом
- [ ] Оговорка про baseline для малых delta ndcg

---

## Связь с deck-data JSON

Поля для `product-default.json` / `proposal_builder.py`:

- `kpi.ndcg_at_20_delta`
- `kpi.zero_reduction_pct`
- `serp_classes.before` / `after`
- `zero_queries_closed[]`
- `sparklines.ndcg`, `sparklines.zero`

---

*Версия: 2026-Q3*
