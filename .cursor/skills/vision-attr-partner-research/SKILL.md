---
name: vision-attr-partner-research
description: >-
  Партнёрский research «атрибуты с картинок»: фид vs фото vs поиск vs ₽.
  Триггеры: vision attrs, атрибуты с картинок, показать партнёру, RESERVE,
  Метрика конверсия, demo cases, playbook ЦУМ, зачем покупать атрибуты.
---

# Vision attr partner research

## Обязательно прочитать

`portfolio/VISION_ATTR_PARTNER_PLAYBOOK.md` — полный пошаговый эталон (ЦУМ).

## Не пропускать

1. **5 кейсов с фото** в HTML (не таблица без картинок) — `PARTNER_DEMO_CASES_TEMPLATE.md`
2. RESERVE/ZERO только из **Diginetica API**, не из CH `isZeroQuery`
3. CVR/AOV для денег — из **Яндекс.Метрики** (`skills-portable/skills/metrika`), AOV = revenue/purchases
4. Таблица «доставать / не доставать» после feed collision
5. **Два денежных стрима** (см. `portfolio/MONEY_TWO_STREAMS_TEMPLATE.md`):
   - A = база по запросам (RESERVE/NORMAL × ΔCVR)
   - B = **доп. потенциал** (категории × P(attr) × выдача) — cons + opt, в шапке презы и секцией после A

## Эталонные скрипты

Префикс `_tsum_*` в корне `attr-enrichment-product` + артефакты `portfolio/tsum/`.

## Deliverable

`portfolio/{partner}/*-image-attrs-research.html` + `MONEY_IMPACT.md` + `demo_cases.json`

## Стрим B (отдельно) — каталог → выдача

Скрипт-эталон: `_tsum_catalog_visibility_money.py`  
Артефакты: `money_catalog_visibility.json`, `MONEY_CATALOG_VISIBILITY.md`  
Не суммировать 1:1 со стримом A (RESERVE/NORMAL × ΔCVR).
