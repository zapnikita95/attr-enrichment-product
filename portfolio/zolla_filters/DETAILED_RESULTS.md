# Zolla Filter Pipeline — DETAILED RESULTS

Updated: 2026-07-21 12:03 UTC

## Budget models (defaults)

- Text (candidacy/schema): `google/gemini-2.5-flash-lite`
- Vision bulk: `google/gemma-3-4b-it`
- Lurex verify only: `google/gemini-2.5-flash-lite` (optional, FILTER_LUREX_VERIFY=0 to skip)
- Premium `gemini-2.5-flash` / `gpt-4o-mini` — только research, не bulk

## Model research (как работают)

### Previous premium bakeoff (hood / pattern)

| Model | tier | hood boolean | print_pattern notes |
|-------|------|--------------|---------------------|
| gemini-2.5-flash | premium | excellent 12/12 | socks OK; lurex miss → need verify |
| gemini-2.5-flash-lite | mid | excellent | lurex OK; socks→меланж miss |
| gpt-4o-mini | mid-high | excellent | lurex miss; costlier |

### Cheap bakeoff (this run)

```json
{
  "cost_notes": {
    "google/gemma-3-4b-it": {
      "tier": "cheap",
      "in_per_m": 0.05,
      "out_per_m": 0.1
    },
    "google/gemini-2.5-flash-lite": {
      "tier": "mid",
      "in_per_m": 0.1,
      "out_per_m": 0.4
    },
    "google/gemini-2.5-flash": {
      "tier": "premium",
      "in_per_m": 0.3,
      "out_per_m": 2.5
    },
    "openai/gpt-4o-mini": {
      "tier": "mid-high",
      "note": "research only, avoid bulk"
    }
  },
  "attrs": {
    "hood": {
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
    },
    "print_pattern": {
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
    },
    "length": {
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
  }
}
```

## Filter candidacy (LLM)

- **Капюшон** → `filter` / boolean: Бинарный атрибут с низкой кардинальностью, который часто является ключевым критерием при выборе верхней одежды.
- **Длина изделия** → `filter` / enum: Ограниченный набор значений (mini, midi, maxi и т.д.) делает этот атрибут подходящим для фильтрации, особенно для платьев и верхней одежды.
- **Узор / принт** → `filter` / multi_enum: Визуальный атрибут с ограниченным набором значений, который помогает покупателям быстро находить желаемый стиль.
- **Длина рукава** → `filter` / enum: Классический атрибут для одежды с небольшим количеством значений, который легко воспринимается покупателями.
- **Карманы** → `filter` / boolean: Бинарный атрибут, важный для функциональности верхней одежды и брюк, с низкой кардинальностью.
- **Застёжка** → `filter` / enum: Ограниченный набор типов застёжек делает этот атрибут удобным для фильтрации, особенно для верхней одежды.
- **Воротник / вырез** → `filter` / enum: Визуальный атрибут с разумной кардинальностью, помогающий покупателям определить желаемый стиль горловины.
- **Пол** → `reject` / None: Атрибут 'Пол' часто уже присутствует в фиде как основной фильтр или является частью названия товара, что делает его избыточным как отдельный facet.
- **Ощущение ткани** → `reject` / None: Это маркетинговый 'fluff' и субъективное описание, которое сложно нормализовать и использовать как точный фильтр.
- **Состав детальный** → `reject` / None: Атрибут 'Состав детальный' имеет высокую кардинальность из-за комбинаций материалов, что делает его непригодным для использования в качестве простого фильтра.
- **Цвет** → `reject` / None: Цвет является стандартным системным фильтром и, как правило, уже присутствует в фиде.
- **Описание ощущения/эффекта** → `reject` / None: Это маркетинговые описания, которые не являются объективными характеристиками товара и не подходят для фильтрации.
- **Размер** → `reject` / None: Размер является стандартным фильтром и обычно обрабатывается как вариант товара, а не как отдельный facet.

## Schema (closed-set filters)

- `hood` (boolean): да, нет
  - why: Бинарный facet с низкой кардинальностью; часто нужен в UI верхней одежды.
  - categories: Верхняя одежда, Платья, Толстовки, Свитшоты
- `length` (enum): mini, midi, maxi, до колена, укороченный
  - why: Ограниченный набор длин — классический facet fashion; не свободный текст.
  - categories: Платья, Юбки, Брюки, Верхняя одежда, Верх
- `print_pattern` (multi_enum): однотонный, полоска, клетка, горошек, цветочный, геометрия, леопард, зебра, тигровый, камуфляж, абстракция, гусиная лапка, меланж, люрекс, графика
  - why: Facet по визуальному узору; кардинальность ограничена closed-set.
  - categories: Верхняя одежда, Платья, Юбки, Брюки, Верх, Аксессуары
- `sleeve_length` (enum): короткий, длинный, 3/4, без рукавов
  - why: Классический facet; 4 значения, хорошо видно на фото.
  - categories: Верхняя одежда, Платья, Верх, Толстовки, Свитшоты
- `pockets` (boolean): да, нет
  - why: Бинарный facet; важен для брюк/верхней одежды.
  - categories: Верхняя одежда, Брюки, Юбки, Платья
- `fastener` (enum): молния, пуговицы, кнопки, завязки, нет
  - why: Ограниченный набор типов застёжки — удобный facet.
  - categories: Верхняя одежда, Платья, Рубашки, Брюки
- `collar` (enum): круглый, V-образный, стойка, отложной, капюшон, без воротника
  - why: Визуальный facet с разумной кардинальностью.
  - categories: Верхняя одежда, Платья, Верх, Рубашки, Толстовки, Свитшоты
- `gender_target` (enum): женский, мужской, унисекс, детский
  - why: Базовый facet каталога; часто уже в фиде — candidacy может reject.
  - categories: Все категории

## Vision pilot results (unique pics → propagate)

| attr | model | unique_pics | offers_after_propagate | coerced_rate | expected_match |
|------|-------|-------------|------------------------|--------------|----------------|
| collar | google/gemma-3-4b-it | 5 | 8 | 1.0 | 0.8 |
| fastener | google/gemma-3-4b-it | 6 | 8 | 1.0 | 1.0 |
| hood | google/gemma-3-4b-it | 8 | 14 | 1.0 | 1.0 |
| length | google/gemma-3-4b-it | 5 | 12 | 1.0 | 1.0 |
| pockets | google/gemma-3-4b-it | 2 | 8 | 1.0 | 1.0 |
| print_pattern | google/gemini-2.5-flash-lite | 12 | 17 | 0.917 | 0.818 |
| sleeve_length | google/gemma-3-4b-it | 5 | 10 | 1.0 | 0.8 |

**Сделано хорошо (≥90% coerce):** collar, fastener, hood, length, pockets, print_pattern, sleeve_length
**Слабо / не дожали:** —

## Demand evidence (ClickHouse) — источник правды по «имеет смысл»

См. `FILTER_DEMAND_EVIDENCE.md` + `query_demand_evidence.json`.
**Без этого файла вердикт «имеет смысл» = не пруф (только LLM/fashion).**

siteId=3826, window=90d, top_n=5000, source=`sessions.searches`

| attr | volume | share% | uniq | verdict |
|------|--------|--------|------|---------|
| `gender_target` | 164329 | 40.8 | 1242 | strong_demand_but_check_feed_nav_collision |
| `color` | 27737 | 6.89 | 531 | strong_demand_but_check_feed_nav_collision |
| `material` | 25744 | 6.39 | 330 | strong_demand_but_check_feed_nav_collision |
| `sleeve_length_product_proxy` | 8875 | 2.2 | 132 | proxy_product_type_not_facet |
| `print_pattern` | 7757 | 1.93 | 151 | strong_filter_candidate |
| `sleeve_length` | 4735 | 1.18 | 107 | strong_filter_candidate |
| `length` | 2512 | 0.62 | 74 | strong_filter_candidate |
| `hood` | 1570 | 0.39 | 44 | strong_filter_candidate |
| `fastener` | 1238 | 0.31 | 50 | strong_filter_candidate |
| `silhouette` | 999 | 0.25 | 29 | strong_filter_candidate |
| `collar` | 570 | 0.14 | 21 | weak_or_sparse |
| `fit_waist` | 137 | 0.03 | 7 | weak_or_sparse |
| `pockets` | 50 | 0.01 | 2 | weak_or_sparse |

## Text gold coerce (3826)

```json
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
```

## Backlog (только если CH strong / collision-checked)

- schema ids сейчас: hood, length, print_pattern, sleeve_length, pockets, fastener, collar, gender_target
- `silhouette` — strong в CH, ещё не в vision pilot
- `color` / `material` / `gender_target` — strong demand, но **feed/nav collision first**
- `fit_waist` / `collar` / `pockets` — weak в топе; category-gated only

## Dedupe rule

Vision вызывается **1 раз на picture_url** (`picture_dedupe.normalize_picture_url`),
затем значение размножается на все `offer_id` с той же картинкой.
