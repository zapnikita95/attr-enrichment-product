# Filter Attribute Pipeline

Полностью LLM-driven процесс: **какие атрибуты → фильтры**, **в каком типе**, **closed-set extract**, **партнёрский proof**.

## Этапы

1. **Inventory** — сырые атрибуты (vision DB / text gold)
2. **Candidacy** — LLM: `filter` / `search_only` / `reject` + мотивация
3. **Schema** — LLM: `boolean` | `enum` | `multi_enum` | `numeric_bins` + `allowed_values`
4. **Typed extract** — vision (OpenRouter) / text — только канон
5. **Hard coerce** — synonym map, OOD reject, feed collision
6. **Partner HTML** — фильтры × категории × pilot metrics (+ CH)

## Zolla pilot

```powershell
cd C:\Users\1\OneDrive\Desktop\attr-enrichment-product
py -3.13 filter_pipeline/run_zolla_pilot.py --stage all
py -3.13 filter_pipeline/run_zolla_pilot.py --stage compare_models --attrs hood
```

Артефакты: `portfolio/zolla_filters/`  
Журнал багов: `filter_pipeline/observations.md`

OpenRouter key берётся из `image_description-main/.env`.

## Demand evidence (обязательно перед «имеет смысл»)

```powershell
py -3.13 filter_pipeline/zolla_query_demand.py
```

Пишет:
- `portfolio/zolla_filters/FILTER_DEMAND_EVIDENCE.md` — пруфы по запросам
- `portfolio/zolla_filters/query_demand_evidence.json` — машинный отчёт
- `portfolio/zolla_filters/zolla_top_queries_90d.json` — топ searchTerm

Источник: ClickHouse `sessions.searches` siteId=**3826**, 90 дней.  
LLM candidacy без этого файла — не считать пруфом спроса.

## Бюджет моделей

| Роль | Модель | Tier |
|------|--------|------|
| Text candidacy/schema | `google/gemini-2.5-flash-lite` | mid |
| Vision bulk (boolean/enum) | `google/gemma-3-4b-it` | **cheap** |
| Vision print_pattern | `google/gemini-2.5-flash-lite` | mid |
| Lurex verify (optional) | flash-lite | mid, `FILTER_LUREX_VERIFY=0` to skip |
| Premium flash / gpt-4o-mini | только research | не bulk |

Дедуп: 1 vision-вызов на `picture_url` → propagate на все offer_id с той же картинкой.
