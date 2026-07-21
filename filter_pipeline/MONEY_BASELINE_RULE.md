# Money baseline: когда CH CVR «сломан»

## Симптом

В `sessions.agg_sessions` search CVR партнёра выглядит абсурдно низко, например:

- Zolla 3826: **0.005%** (10 search-заказов / ~195k search-сессий за 90д)
- При этом поисков много (`sessions.searches` сотни тысяч) — **объём поиска живой**, ломается именно учёт заказов (`withOrder`).

Порог «сломано»: **search_cvr_pct &lt; 0.05%** (абсолютных).

## Что делать (порядок)

1. **Яндекс.Метрика партнёра** (если есть counter + search goal в `skills/metrika` / `benchmarks/collect_data.METRIKA_MAPPING`).
   - Ecommerce: visits / purchases / revenue
   - Сегмент поиска: `ym:s:goal{GOAL}IsReached=='Yes'`
   - Zolla: counter `79438447`, goal `294554663` → search CVR **~4.8%**, AOV ~2600 ₽ (90д).

2. Если Метрики нет / сегмент пустой → **бенчмарк похожих партнёров**:
   - Airtable CRM (`Вертикаль` ≈ одежда/fashion/обувь) → список `site_id`
   - Медиана **search CVR** по Метрике peers (если есть goal)
   - Медиана **search CVR** по ClickHouse peers с CVR ≥ 0.05% (исключить сломанные)

3. Если ничего нет → ASSUMED vertical floor (явно пометить), не писать «0.005% возможно недоучёт» как рабочую базу денег.

## Lift — только от бенчмарков, не «с потолка»

Если на партнёре ещё нет facet with/without:

1. Взять измеренные **сессии с фильтрами vs без** с других проектов Diginetica (`portfolio/filter-conversion-data.json`).
2. Считать **относительный** lift (CVR_with / CVR_without − 1), положительные категории.
3. Для sketch новых facet — полоса **+15…+25%** относительно (как в TSUM NORMAL), не выдуманные +0.5 п.п. на крошечном пуле.
4. Формула партнёра:  
   `Δ₽_90д = выручка_поиска_Метрика × доля_затронутых × adoption × relative_lift`

## Партнёрская преза (обязательно)

**Нельзя** в HTML для партнёра:

- битый CH CVR («0.005% не использовать», «10 заказов / 195k»)
- имена других брендов/партнёров в бенчмарке
- внутренние пути (`MONEY_BASELINE_RULE.md`, `money_baseline_benchmark.json`)

Внутри JSON / agent notes — можно. В §«Деньги» презы — только Метрика партнёра + анонимный бенчмарк Diginetica + ₽ и **% от выручки поиска**.

## Zolla кейс (проверено 2026-07-21)

| Источник | Search CVR | AOV |
|----------|------------|-----|
| CH Zolla | 0.005% ❌ | 3396 ₽ |
| Metrika Zolla search | **4.809%** ✅ | **2613 ₽** |
| Peer Metrika median (Zarina/Ecco/TSUM…) | ~4.2% | — |
| Peer CH median (Befree, Gloria, RV, Zarina…) | ~2.9% | — |

Вывод: Zolla Metrika согласуется с fashion-бенчмарком; CH orders undercount.

## Скрипты

```powershell
py -3.13 filter_pipeline/zolla_money_benchmark.py   # Metrika + peers
py -3.13 filter_pipeline/_ch_peers_only.py          # быстрый CH refresh
py -3.13 filter_pipeline/build_zolla_partner_defense.py
```

Артефакт: `portfolio/zolla_filters/money_baseline_benchmark.json`
