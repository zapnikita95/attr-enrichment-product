# Zolla Filter Pipeline — Observations

Живой журнал пилота (OpenRouter, site/project 3826).

## Stage 2 — Filter candidacy (`google/gemini-2.5-flash`)

- **Капюшон / Длина / Узор** → `filter` с корректными типами (boolean / enum / multi_enum).
- **Ощущение ткани**, **Состав детальный** → `reject` (субъективность / высокая кардинальность).
- **Цвет** → `reject` как дубль фида (разумный default; для партнёров без color facet можно вернуть в filter).

## Stage 3 — Schema

LLM вернул closed-set:
- hood: `да|нет`
- length: `mini|midi|maxi|до колена|укороченный`
- print_pattern: 15 канонов (полоска…люрекс)

Синонимы от LLM короткие — **обязательно мержить seed synonym_map** (иначе text gold почти весь OOD).

## Stage 4 — Vision

### Bug: image cache key

Первый прогон hood: `failed to download` + модель «нет» на пальто с капюшоном — брали **не тот** local path (md5), картинки не находились.
**Fix:** ключ как в `attribute_detector._image_cache_path`: `sha256(url)[:24].jpg`.

После фикса: hood **12/12** coerced, **12/12** match expected. Все raw строго `да|нет` (без «есть/капюшон»).

### length

10/10 coerced + expected. Один raw `мини` → coerce `mini` (синоним). Closed-set работает.

### print_pattern

| Модель | 96863 melange | 100889 lurex | 94603 graphics |
|--------|---------------|--------------|----------------|
| gemini-2.5-flash | OK | FAIL→меланж | OK |
| gemini-2.5-flash-lite | OK | OK | FAIL→меланж |
| gpt-4o-mini | OK | FAIL→меланж | OK |

**Fix:** primary = flash, second-pass lurex verify = flash-lite when value ∈ {меланж, однотонный}.
Итог control+stripes: **9/9** expected match (100889 починился через verify).

### hood model bakeoff

Все три модели 6/6 на yes-выборке (палько/парки). Для boolean flash достаточно; flash-lite чуть дешевле.

## Stage 4b — Text gold coerce

После synonym merge:
- length: 13/22 ok (остальное — «закруглённая кромка» и т.п. → правильно OOD, это не facet длины)
- print_pattern: 83/178 ok (остальное свободные фразы gold; нужен typed re-extract, не только coerce)

**Вывод:** Scenario B (discover) требует schema→typed extract по описанию, а не post-hoc coerce сырого gold.

## Infra

- OpenRouter через proxy `127.0.0.1:18080`, key из `image_description-main/.env`.
- Локальные vision-модели не трогали.

## Partner metrics

Формула CH в `ch_filter_metrics.py` (demo на 4lapy `filter-conversion-data.json`).
Zolla CH pull site_id=3826 — следующий шаг (нужны facet events / baseline категории).

## Stage 6 — Partner HTML (2026-07-21 11:16 UTC)

Wrote `C:\Users\1\OneDrive\Desktop\attr-enrichment-product\portfolio\zolla_filters\zolla-filter-impact.html`
