# Шаблон: два денежных стрима (всегда для vision-attrs)

> **Обязательно** в каждом партнёрском research / HTML / презе.  
> Эталон: ЦУМ (`portfolio/tsum/`, `_tsum_catalog_visibility_money.py`).

## Зачем два слоя

| Стрим | Что считает | Партнёру |
|-------|-------------|----------|
| **A — запросы** | RESERVE/NORMAL × fixable × ΔCVR × AOV (Метрика) | **База** «починим уже идущий поиск» |
| **B — выдача** | категории × P(новый attr на SKU) × попадание в SERP × CTR × purchase\|click × AOV | **Доп. потенциал** «товары начнут показываться» |

B — не замена A. Не суммировать 1:1 без пометки «частичное пересечение спроса».

## Что всегда положить в презу

1. В шапке: цифра A (base) + диапазон B (cons…opt) с плюсом.  
2. Callout «два денежных слоя».  
3. Секция **после** денег A: `Доп. потенциал (стрим B)` с таблицей по категориям.  
4. В CTA: «база X ₽/мес + доп. потенциал +Y…+Z ₽/мес».

## Формула B (защищаемая гипотеза)

```text
attr_demand = family_searches × bucket_share × attr_gated_share
newly_eligible = p_extract × (1 − coverage_now)
p_in_serp = min(cap, newly_eligible × serp_factor)
extra_impressions = attr_demand × p_in_serp
Δ₽_90д = extra_impressions × CTR × purchase|click × AOV_Метрика
```

- **Conservative:** `direct_facet`, gated ~85%, ниже CTR / P(extract).  
- **Optimistic:** `expanded_style`, gated ~35% (type-nouns часто уже в фиде), выше воронка.

## Чеклист перед отправкой партнёру

- [ ] Стрим A на Метрике (не сырой CH search CVR, если занижает)
- [ ] Стрим B посчитан (cons + opt), файл `MONEY_CATALOG_VISIBILITY.md`
- [ ] В HTML секция 8b / аналог с формулировкой **«доп. потенциал»**
- [ ] По категориям видно, где лежат деньги (обувь / сумки / одежда…)
- [ ] Явно сказано: B сверху базы A, не «вместо»

## Артефакты

- `money_impact_metrika.json` / `MONEY_IMPACT.md` — стрим A  
- `money_catalog_visibility.json` / `MONEY_CATALOG_VISIBILITY.md` — стрим B  
- Partner HTML: маркеры `<!-- CATALOG_VISIBILITY_STREAM -->`

## Скрипт-эталон

```powershell
py -3.13 _tsum_catalog_visibility_money.py
```

Для нового партнёра — скопировать логику бакетов/гипотез под его категории и lexicon.
