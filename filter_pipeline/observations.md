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

## Stage 2 — Filter candidacy (2026-07-21 11:45 UTC)

- model: `google/gemini-2.5-flash-lite`
- decisions: 13
- **Капюшон** → `filter` (boolean): Бинарный атрибут с низкой кардинальностью, который часто является ключевым критерием при выборе верхней одежды.
- **Длина изделия** → `filter` (enum): Ограниченный набор значений (mini, midi, maxi и т.д.) делает этот атрибут подходящим для фильтрации, особенно для платьев и верхней одежды.
- **Узор / принт** → `filter` (multi_enum): Визуальный атрибут с ограниченным набором значений, который помогает покупателям быстро находить желаемый стиль.
- **Длина рукава** → `filter` (enum): Классический атрибут для одежды с небольшим количеством значений, который легко воспринимается покупателями.
- **Карманы** → `filter` (boolean): Бинарный атрибут, важный для функциональности верхней одежды и брюк, с низкой кардинальностью.
- **Застёжка** → `filter` (enum): Ограниченный набор типов застёжек делает этот атрибут удобным для фильтрации, особенно для верхней одежды.
- **Воротник / вырез** → `filter` (enum): Визуальный атрибут с разумной кардинальностью, помогающий покупателям определить желаемый стиль горловины.
- **Пол** → `reject` (None): Атрибут 'Пол' часто уже присутствует в фиде как основной фильтр или является частью названия товара, что делает его избыточным как отдельный facet.
- **Ощущение ткани** → `reject` (None): Это маркетинговый 'fluff' и субъективное описание, которое сложно нормализовать и использовать как точный фильтр.
- **Состав детальный** → `reject` (None): Атрибут 'Состав детальный' имеет высокую кардинальность из-за комбинаций материалов, что делает его непригодным для использования в качестве простого фильтра.
- **Цвет** → `reject` (None): Цвет является стандартным системным фильтром и, как правило, уже присутствует в фиде.
- **Описание ощущения/эффекта** → `reject` (None): Это маркетинговые описания, которые не являются объективными характеристиками товара и не подходят для фильтрации.
- **Размер** → `reject` (None): Размер является стандартным фильтром и обычно обрабатывается как вариант товара, а не как отдельный facet.

## Stage 3 — Type + vocabulary (2026-07-21 11:45 UTC)

- model: `google/gemini-2.5-flash-lite`
- attrs: 8
- **hood** `boolean` allowed=['да', 'нет']
- **length** `enum` allowed=['mini', 'midi', 'maxi', 'до колена', 'укороченный']
- **print_pattern** `multi_enum` allowed=['однотонный', 'полоска', 'клетка', 'горошек', 'цветочный', 'геометрия', 'леопард', 'зебра', 'тигровый', 'камуфляж', 'абстракция', 'гусиная лапка', 'меланж', 'люрекс', 'графика']
- **sleeve_length** `enum` allowed=['короткий', 'длинный', '3/4', 'без рукавов']
- **pockets** `boolean` allowed=['да', 'нет']
- **fastener** `enum` allowed=['молния', 'пуговицы', 'кнопки', 'завязки', 'нет']
- **collar** `enum` allowed=['круглый', 'V-образный', 'стойка', 'отложной', 'капюшон', 'без воротника']
- **gender_target** `enum` allowed=['женский', 'мужской', 'унисекс', 'детский']

## Model bakeoff `hood` (cheap) (2026-07-21 11:45 UTC)

{
  "models": {
    "google/gemma-3-4b-it": {
      "coerced_rate": 1.0,
      "expected_match_rate": 1.0,
      "n": 4,
      "tier": "cheap"
    },
    "google/gemini-2.5-flash-lite": {
      "coerced_rate": 1.0,
      "expected_match_rate": 1.0,
      "n": 4,
      "tier": "mid"
    }
  },
  "best": "google/gemma-3-4b-it"
}

## Model bakeoff `print_pattern` (cheap) (2026-07-21 11:46 UTC)

{
  "models": {
    "google/gemma-3-4b-it": {
      "coerced_rate": 1.0,
      "expected_match_rate": 0.0,
      "n": 4,
      "tier": "cheap"
    },
    "google/gemini-2.5-flash-lite": {
      "coerced_rate": 1.0,
      "expected_match_rate": 0.75,
      "n": 4,
      "tier": "mid"
    }
  },
  "best": "google/gemini-2.5-flash-lite"
}

## Model bakeoff `length` (cheap) (2026-07-21 11:46 UTC)

{
  "models": {
    "google/gemma-3-4b-it": {
      "coerced_rate": 1.0,
      "expected_match_rate": 1.0,
      "n": 4,
      "tier": "cheap"
    },
    "google/gemini-2.5-flash-lite": {
      "coerced_rate": 0.75,
      "expected_match_rate": 1.0,
      "n": 4,
      "tier": "mid"
    }
  },
  "best": "google/gemma-3-4b-it"
}

## Stage 4 — Vision typed extract `hood` (2026-07-21 11:47 UTC)

- model: `google/gemma-3-4b-it` (budget default)
- unique_pics: 8 / offers: 14 (propagated 6)
- coerced_rate: 1.0 (8/8)
- expected_match_rate: 1.0
- issues:
  - none

## Stage 4 — Vision typed extract `length` (2026-07-21 11:47 UTC)

- model: `google/gemma-3-4b-it` (budget default)
- unique_pics: 5 / offers: 12 (propagated 7)
- coerced_rate: 1.0 (5/5)
- expected_match_rate: 1.0
- issues:
  - none

## Stage 4 — Vision typed extract `print_pattern` (2026-07-21 11:48 UTC)

- model: `google/gemini-2.5-flash-lite` (budget default)
- unique_pics: 12 / offers: 17 (propagated 5)
- coerced_rate: 0.917 (11/12)
- expected_match_rate: 0.818
- issues:
  - 18781: FAIL raw='' reason=empty

## Stage 4 — Vision typed extract `sleeve_length` (2026-07-21 11:48 UTC)

- model: `google/gemma-3-4b-it` (budget default)
- unique_pics: 5 / offers: 10 (propagated 5)
- coerced_rate: 0.8 (4/5)
- expected_match_rate: 0.75
- issues:
  - 15873: FAIL raw='без рукавов' reason=negation

## Stage 4 — Vision typed extract `pockets` (2026-07-21 11:49 UTC)

- model: `google/gemma-3-4b-it` (budget default)
- unique_pics: 2 / offers: 8 (propagated 6)
- coerced_rate: 1.0 (2/2)
- expected_match_rate: 1.0
- issues:
  - none

## Stage 4 — Vision typed extract `fastener` (2026-07-21 11:49 UTC)

- model: `google/gemma-3-4b-it` (budget default)
- unique_pics: 6 / offers: 8 (propagated 2)
- coerced_rate: 1.0 (6/6)
- expected_match_rate: 1.0
- issues:
  - none

## Stage 4 — Vision typed extract `collar` (2026-07-21 11:49 UTC)

- model: `google/gemma-3-4b-it` (budget default)
- unique_pics: 5 / offers: 8 (propagated 3)
- coerced_rate: 1.0 (5/5)
- expected_match_rate: 0.8
- issues:
  - none

## Stage 4 — Vision typed extract `sleeve_length` (2026-07-21 11:50 UTC)

- model: `google/gemma-3-4b-it` (budget default)
- unique_pics: 5 / offers: 10 (propagated 5)
- coerced_rate: 1.0 (5/5)
- expected_match_rate: 0.8
- issues:
  - none

## Stage 4b — Text gold coerce (2026-07-21 11:50 UTC)

{
  "collar": {
    "seen": 113,
    "ok": 90,
    "collision": 0,
    "ood": 23
  },
  "pockets": {
    "seen": 27,
    "ok": 1,
    "collision": 0,
    "ood": 26
  },
  "sleeve_length": {
    "seen": 57,
    "ok": 43,
    "collision": 0,
    "ood": 14
  },
  "length": {
    "seen": 3,
    "ok": 3,
    "collision": 0,
    "ood": 0
  }
}

## Stage 6 — Partner HTML (2026-07-21 11:50 UTC)

Wrote `C:\Users\1\OneDrive\Desktop\attr-enrichment-product\portfolio\zolla_filters\zolla-filter-impact.html`
