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
