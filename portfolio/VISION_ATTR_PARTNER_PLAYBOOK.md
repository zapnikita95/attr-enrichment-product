# Playbook: атрибуты с картинок → партнёрский research с деньгами

> **Зачем этот документ.** Это эталон, как продавать / защищать продукт *vision attributes*:  
> не «мы умеем OCR», а **наглядный разрыв фид ↔ фото ↔ поиск ↔ ₽**.  
> Эталонный прогон: **ЦУМ (site 203)**, июль 2026.  
> Повторять на любом fashion / beauty / luxury партнёре с YML + Diginetica + Метрикой.

---

## 0. Что должно получиться у партнёра в голове

Одна мысль:

> «У нас в фиде уже есть бренд/цвет/материал.  
> Но покупатель ищет **полоску, каблук, хобо, капюшон** — этого в индексе нет,  
> а на фото это видно. Вы это достаёте. Вот 5 карточек. Вот запасные запросы. Вот ₽.»

Артефакты deliverable (без прайса услуги, но **с оценкой выручки**):

| Файл | Роль |
|------|------|
| `portfolio/{partner}/{partner}-image-attrs-research.html` | Главный партнёрский HTML |
| `portfolio/{partner}/demo_cases.json` + секция «5 кейсов» | Наглядность |
| `portfolio/{partner}/MONEY_IMPACT.md` | Деньги отдельно |
| `portfolio/{partner}/VISION_ATTR_DECISION.md` | KEEP / НЕ доставать |
| Canvas (опционально) | Для внутреннего разбора в Cursor |

---

## 1. Входы (что нужно до старта)

1. **YML-фид** партнёра (полный, с `<picture>`, `<param>`, деревом `<category>`).
2. **site_id** Diginetica + **apiKey** sort API  
   (пример ЦУМ: site `203`, key из URL `sort.diginetica.net/search?...&apiKey=...`).
3. Доступ к **ClickHouse** `sessions.*` (топ запросов, zero-flag — *вспомогательно*).
4. Доступ к **Яндекс.Метрике** (скилл `skills-portable/skills/metrika`):  
   `site_id → counter_id`, OAuth token diginetica.office.  
   ЦУМ: counter **21801616**.
5. **OpenRouter** ключ (`OPENROUTER_API_KEY` в image_description `.env`) — vision **не локалки**.

---

## 2. Сквозной пайплайн (порядок шагов)

```text
1. Inventory фида          → что УЖЕ есть (params fill, name)
2. CH top queries          → что ищут (частоты)
3. Needle / lexicon gap    → какие стилевые слова не в фиде
4. OpenRouter vision probe → что ВИДНО на фото (new vs feed)
5. KEEP/REJECT             → feed collision, негации, мусор
6. Diginetica API classify → ZERO / RESERVE / NORMAL на impact-запросах
7. Метрика CVR + AOV       → честные деньги (не CH search-атрибуция)
8. Money calc              → Δ ₽/мес
9. 5 demo cases + HTML     → парт продукта картинками
```

Ниже — каждый шаг в деталях.

---

## 3. Шаг 1 — Inventory фида (истина о каталоге)

**Скрипт-эталон:** `_tsum_feed_inventory.py`  
**Выход:** `feed_inventory.json`, `vision_candidates.json`, `categories.json`

### Что делать

- Stream-parse YML (`iterparse`) — фид может быть **гигабайты** (ЦУМ ~1.5 GB, ~664k offer).
- Собрать:
  - список уникальных `param name` + fill % + примеры значений;
  - дерево категорий + top categories by offers;
  - выборку SKU с картинками по priority buckets (`odezhda`, `platya`, `obuv`, `sumki`, `parfyumeriya`, …).

### Как читать результат (логика продажи)

Разделить params на:

| Класс | Примеры ЦУМ | Вывод для партнёра |
|-------|-------------|--------------------|
| **Уже закрыто** | Пол, Цвет, Оттенок, Материал %, Размер, бренд в name | С картинок **не дублировать** |
| **Технические** | brand_id, color_*_id, size_id, Артикул, Лого-URL | Не search-атрибуты |
| **Дыры** | нет «принт/узор»; `attribute_details` ~8%; `attribute_clasp` ~2% | Зона vision |

### Важно: проверять и **названия**

Недостаточно сказать «нет param Принт». Прогнать лексику по `name` ∪ params:

**Скрипт:** `_tsum_check_pattern_in_names.py` → `pattern_name_coverage.json`

Пример ЦУМ: «клетк*» в name ~0.04%, «полоск*» ~0.07%, любая pattern-лексика в `name ∪ params` ~**2.7%** каталога.  
Формулировка для партнёра: «в названиях почти нет — системного покрытия узора нет».

---

## 4. Шаг 2 — ClickHouse: что ищут

**Скрипт:** `_tsum_ch_queries.py`, `_tsum_ch_totals.py`  
**Выход:** `top-30k-queries-ch.json`, `ch_totals_90d.json`

```sql
SELECT lowerUTF8(trim(searchTerm)) AS q, count() AS cnt,
       countIf(isZeroQuery = 'true') AS zero_cnt
FROM sessions.searches
WHERE siteId = {SITE}
  AND timestamp >= now() - INTERVAL 90 DAY
GROUP BY q
ORDER BY cnt DESC
LIMIT 30000
```

**Найти site_id**, если не знаешь:

```sql
SELECT siteId, count() AS cnt
FROM sessions.searches
WHERE timestamp >= now() - INTERVAL 3 DAY
  AND (remoteHost ILIKE '%tsum%' OR location ILIKE '%tsum%' OR referer ILIKE '%tsum%')
GROUP BY siteId
ORDER BY cnt DESC
```

ЦУМ → **203** (`mapi.tsum.ru` в location).

### ⚠️ Ловушка CH

`isZeroQuery='true'` в CH **≠** Diginetica RESERVE.  
Часто CH помечает zero, а API отвечает `zeroQueries=false` и `totalHits>0`.  
Для классификации запасных **всегда API** (шаг 6).

CH всё равно нужен: частоты запросов, топ нулевых-флагов, грубый объём поиска.

---

## 5. Шаг 3 — Lexicon / needle gap (на что можем повлиять)

**Скрипты:** `_tsum_gap_and_needles.py`, `_tsum_impact_refine.py`  
**Выход:** `gap_analysis.json`, `query_impact_refined.json`

### Идея

1. Построить корпус индексируемого фида: `name + params` (без id / лого-URL / описания-простыни).
2. Токены запросов, которых нет в корпусе → residual.
3. Отдельно — **семейства vision-лексики** (needles):

   - принт / клетка / полоска / леопард  
   - оверсайз / клеш / slim  
   - капюшон  
   - на каблуке / платформа / шпилька  
   - кроссбоди / тоут / клатч / багет  
   - застёжка / стразы / пайетки  
   - парфюм / туалетная вода / ноты  

Два тира для честности:

| Тир | Смысл | ЦУМ 90д (примерно) |
|-----|--------|---------------------|
| **direct_facet** | Буквальные facet-формулировки | ~116k поисков |
| **expanded_style** | Шире стилевая лексика | ~297k поисков |

Механика близка к `attributes_extraction` lexicon/feed-collision:  
**не считаем gap’ом то, что уже в name/params.**

---

## 6. Шаг 4 — Vision probe (OpenRouter, не локалки)

**Скрипт:** `_tsum_openrouter_vision_probe.py`  
**Модель:** `google/gemini-2.5-flash` (или flash-lite для OCR-массовости)  
**Выход:** `vision_probe_results.json`

### Промпт (суть)

- Дать модели **картинку** + список «уже в фиде» (params без id).
- Явно запретить: цвет/материал/бренд/артикул если уже есть; негации «без X».
- Просить JSON: `new_attributes[]`, `already_in_feed_visible`, `evidence: visual|ocr`.

### Выборка

Не 1 категория. **Диверсификация** по бакетам, которые ищут и которые большие в каталоге:  
одежда, платья, обувь, сумки, парфюм, косметика, часы, верхняя, джинсы…  
ЦУМ: **28 SKU**, у всех нашлись кандидаты → после фильтра KEEP.

### Oversight

На длинном vision-прогоне — `llm-output-overseer`: отсечь feed collision / галлюцинации  
(пример: «концентрация» уже в названии парфюма; CHRONOMETER ≠ хронограф).

---

## 7. Шаг 5 — KEEP / REJECT (защита от «вы нам нальёте мусор»)

**Скрипт:** `_tsum_vision_decision.py`  
**Выход:** `vision_attr_decision.json`, `VISION_ATTR_DECISION.md`

### НЕ доставать с картинок

- Цвет / Оттенок / Материал % / Пол / Размер / бренд / артикул / id  
- length/sleeve **где уже заполнены**  
- Негации («без сахара», «-free») — ломают поиск  
- Маркетинг низкой search relevance («эффект: комфорт») как главный deliverable

### ДОСТАВАТЬ

- Принт / узор  
- Силуэт / посадка  
- Капюшон, воротник / вырез  
- Застёжка (если clasp sparse)  
- Декор / фактура  
- Тип сумки, каблук / форма обуви  
- OCR парфюма / часов — только если нет в name/params  

Это таблица «нужно / не нужно» — **обязательна** в отчёте. Иначе партнёр думает, что вы дублируете фид.

---

## 8. Шаг 6 — Diginetica API: ZERO / RESERVE / NORMAL

**Скрипт:** `_tsum_api_classify_impact.py`  
**Эндпоинт:** `https://sort.diginetica.net/search`  
**Стратегия (как у партнёра):** `advanced_xname,zero_queries_predictor`  
**size=0**, single-thread (ThreadPool кладёт API).

### Классификация

| Условие | Тип | Смысл для денег |
|---------|-----|-----------------|
| `totalHits == 0` | **ZERO** | Товаров в выдаче нет |
| `totalHits > 0` и `zeroQueries == true` | **RESERVE** | Товары есть, но точного матча нет — запасная выдача ★ |
| `zeroQueries == false` | **NORMAL** | Выдача работает — можно улучшить точность |

### На чём гонять API

Не все 30k. Только **impact-пул** (vision needles из шага 3).  
ЦУМ: 1506 запросов → **356 RESERVE / 0 ZERO / 1148 NORMAL**.

### Сверка с CH

Если CH zero-flag и API NORMAL расходятся — **верить API**.  
Документировать число disagree (ЦУМ: ~102).

---

## 9. Шаг 7 — Яндекс.Метрика: честная конверсия и чек

**Скилл:** `C:\Users\1\OneDrive\Desktop\skills-portable\skills\metrika\SKILL.md`  
**Скрипты:** `_tsum_metrika_cvr.py`, `_tsum_metrika_verify.py`  
**Выход:** `metrika_cvr_clean.json`

### Почему не только CH

У ЦУМ Diginetica CH search-session CVR выходил **~0.08%** — атрибуция заказов к поиску дырявая.  
В Метрике на том же периоде:

| Метрика | Значение (ЦУМ, 90д) |
|---------|---------------------|
| Counter | 21801616 |
| CVR сайта (ecom/visits) | **0.309%** |
| CVR **с поиском** (автоцель 260498358) | **1.211%** |
| CVR без поиска | **0.280%** |
| Lift поиск vs без | **×4.3** |
| AOV поиска | **~106.7k ₽** = `ecommerceRevenue / ecommercePurchases` |

### Как дергать

1. `GET /management/v1/counter/{id}` — счётчик жив?  
2. `GET .../goals` — найти цель «поиск» / type=search.  
3. `GET /stat/v1/data` с  
   `metrics=ym:s:visits,ym:s:ecommercePurchases,ym:s:ecommerceRevenue`  
   и фильтром `ym:s:goal{GOAL}IsReached=='Yes'|'No'`.

**⚠️** Не доверять слепо `ym:s:avgPurchaseRevenue` на этом счётчике — считать AOV сами: `revenue/purchases`.

Маппинг site→counter: в SKILL.md и `benchmarks/collect_data.py` (203 → 21801616).

---

## 10. Шаг 8 — Деньги (формула, которую можно защищать)

**Скрипт:** `_tsum_money_recalc_metrika.py`  
**Выход:** `money_impact_metrika.json`, `MONEY_IMPACT.md`

### Формула

```text
ΔВыручка_90д = Σ searches × fixable × (CVR_new − CVR_old) × AOV
Δ/мес = Δ_90д / 3
Δ/год = Δ/мес × 12
```

| Переход | CVR_old | CVR_new | fixable (доля объёма) |
|---------|---------|---------|------------------------|
| RESERVE → точный | ~40% от search CVR (или 0 если измерено) | CVR поиска из Метрики | 0.7–0.9 |
| NORMAL → точнее | CVR поиска | CVR × (1 + 0.15…0.25) | 0.25–0.45 |
| ZERO → найдено | 0 | 0.5 × CVR поиска | 0.4–0.6 |

### Сценарии

Всегда три: **conservative / base / optimistic**.  
Партнёру в шапке — **base**.

### ЦУМ base (после Метрики)

- RESERVE 12.8k поисков + NORMAL 306k  
- **~11.9M ₽/мес** · **~142M ₽/год**  
- (консерв. ~7.3M / оптим. ~21M ₽/мес)

Без Метрики (на CH 0.08%) получалось ~0.9M/мес — **не показывать** как основное.

---

## 10b. Стрим B — каталог × категории × доп. выдача (отдельно)

**Зачем:** показать деньги не только от «починки» RESERVE/NORMAL, а от того, что SKU с новыми attr **начинают появляться в SERP**.

**Скрипт:** `_tsum_catalog_visibility_money.py`  
**Выход:** `money_catalog_visibility.json`, `MONEY_CATALOG_VISIBILITY.md`, блок `6b` в HTML.

### Логика

1. Скатать фид в бакеты (одежда / верхняя / обувь / сумки / парфюм / аксессуары) — offers по slug URL.  
2. Разметить top-30k CH-запросов по keywords → **сколько ищут категорию**.  
3. Attr-спрос бакета = семьи из `query_impact_refined` (`direct_facet` / `expanded_style`) × `attr_gated_share`.  
4. Гипотеза на SKU: `p_extract` (достанем новый searchable attr) и `coverage_now` (уже есть в фиде).  
5. Воронка: eligible → попадание в выдачу → CTR → purchase|click → × AOV Метрики.

```text
newly_eligible = p_extract × (1 − coverage_now)
extra_impressions = attr_demand × P(session gets new SKU in SERP)
Δ₽ = extra_impressions × CTR × purchase|click × AOV
```

### ЦУМ (порядок величины)

| | ₽/мес | ₽/год |
|---|---:|---:|
| Conservative | ~1.9M | ~23M |
| Optimistic | ~12M | ~149M |

**Не суммировать 1:1 со стримом A** — пересечение attr-спроса. Партнёру: «стрим A = качество матчинга запросов; стрим B = доп. товары в выдаче».

---

## 11. Шаг 9 — Пять наглядных кейсов (защита продукта)

Это **самое важное для «ахуительно наглядно»**.  
Таблица attr→value без фото партнёра не убеждает.

**Скрипты:** `_tsum_pick_demo_cases.py`, `_tsum_build_demo_html.py`  
**Шаблон:** `PARTNER_DEMO_CASES_TEMPLATE.md`  
**Правило Cursor:** `.cursor/rules/partner-visual-demo-cases.mdc`

### Структура одного кейса

```
[фото 200×200+]
Товар · бренд · offer_id · ссылка на карточку

Одна фраза: чего не было в фиде и что видно на фото.

| Уже было в фиде          | Достали с картинки        |
| Пол, Цвет, Материал…     | Принт: Полоска (visual)   |
```

### Критерии отбора 5 штук

1. KEEP после feed-collision.  
2. Разные категории.  
3. Атрибут бьётся в поиск (принт, каблук, хобо, капюшон…).  
4. Не маркетинг («эффект: комфорт») как герой-кейс.  
5. Картинка реально читается (не заглушка).

### Эталон ЦУМ

| # | Товар | Было в фиде | С фото |
|---|-------|-------------|--------|
| 1 | Костюм BOSS | цвет, шерсть, рукав | **Принт: полоска**, пуговицы, посадка |
| 2 | Платье Diesel | цвет, рукав | **Вырез-капля**, стойка, молния |
| 3 | Сумка Vic Matie | кожа, цвет, «через плечо» | **Силуэт: хобо**, одна ручка |
| 4 | Куртка Herno | утеплённая, рукав | **Капюшон: есть**, молния |
| 5 | Пальто D&G | цвет, материал | **Клетка тартан**, стёжка |

В HTML — **до** блока денег. Партнёр сначала видит качество, потом ₽.

---

## 12. Структура партнёрского HTML (порядок секций)

1. Headline + 6 цифр (SKU, поиски, RESERVE, CVR Метрика, Δ ₽/мес, AOV)  
2. Что уже в фиде  
3. **Не** доставать с картинок  
4. **Нужно** доставать с картинок  
5. **Наглядные кейсы (фото)** ← сердце  
6. Конверсия Метрики (с проверкой API)  
7. Пул ZERO/RESERVE/NORMAL + топ запасных  
8. Δ выручка (3 сценария)  
9. Методология коротко + источники  

Без прайса пакета услуг, если не просили — но **оценка выручки обязательна**.

---

## 13. Чеклист «можно показывать партнёру»

- [ ] Params: нужно / не нужно — явно  
- [ ] Names проверены (не только params)  
- [ ] Vision через OpenRouter, модель названа  
- [ ] KEEP после collision; oversight на галлюцинации  
- [ ] **5 кейсов с фото** и one-liner  
- [ ] RESERVE из **API**, не из CH isZero  
- [ ] CVR/AOV из **Метрики**, AOV = revenue/purchases  
- [ ] Три сценария ₽ стрима A; base выделен
- [ ] Стрим B (доп. потенциал выдачи) cons+opt в шапке и секции после A — `MONEY_TWO_STREAMS_TEMPLATE.md`  
- [ ] Формула написана  
- [ ] Период данных (90д) и site_id/counter указаны  
- [ ] Нет секретов в git (токены Метрики не коммитить в публичные доки — только в SKILL)

---

## 14. Карта скриптов (ЦУМ-эталон в корне `attr-enrichment-product`)

| Скрипт | Шаг |
|--------|-----|
| `_tsum_feed_inventory.py` | Inventory |
| `_tsum_ch_find_site.py` / `_tsum_ch_queries.py` / `_tsum_ch_totals.py` | CH |
| `_tsum_gap_and_needles.py` / `_tsum_impact_refine.py` | Lexicon |
| `_tsum_check_pattern_in_names.py` | Name coverage |
| `_tsum_openrouter_vision_probe.py` | Vision |
| `_tsum_vision_decision.py` | KEEP/REJECT |
| `_tsum_api_classify_impact.py` | Reserve API |
| `_tsum_metrika_verify.py` / `_tsum_metrika_cvr.py` | Метрика |
| `_tsum_money_recalc_metrika.py` | ₽ |
| `_tsum_pick_demo_cases.py` / `_tsum_build_demo_html.py` | Кейсы + HTML |
| `_tsum_build_partner_report.py` | Каркас HTML |

Артефакты: `portfolio/tsum/`.

---

## 15. Как запускать на новом партнёре (короткий рецепт)

```powershell
# 1) Положить фид, выставить SITE / API_KEY / COUNTER в скриптах или env
# 2) Inventory + CH top
py -3.13 _partner_feed_inventory.py
py -3.13 _partner_ch_queries.py

# 3) Impact needles + vision (OpenRouter)
py -3.13 _partner_impact_refine.py
py -3.13 _partner_openrouter_vision_probe.py
py -3.13 _partner_vision_decision.py

# 4) API reserve + Metrika + money
py -3.13 _partner_api_classify_impact.py
py -3.13 _partner_metrika_verify.py
py -3.13 _partner_money_recalc_metrika.py

# 5) Demo + HTML
py -3.13 _partner_pick_demo_cases.py
py -3.13 _partner_build_demo_html.py
```

Пока скрипты с префиксом `_tsum_` — копировать и заменить константы (`SITE`, `API_KEY`, `COUNTER`, пути фида, buckets).

---

## 16. Почему это «защищает продукт»

1. **Не спорим с фидом** — сами говорим, что цвет/материал уже есть.  
2. **Показываем дыру** — принт/каблук/хобо в запросах есть, в индексе нет.  
3. **Доказываем качество** — 5 фото «было / стало», не абстрактный LLM.  
4. **Доказываем спрос** — RESERVE из боевого API.  
5. **Доказываем деньги** — Метрика CVR×AOV, не «поверьте на слово».  
6. **Консервативность** — fixable < 100%, три сценария, явная формула.

Именно связка **фото-кейсы + RESERVE + Метрика-₽** делает исследование неотличимым от «продающего аудита», а не от внутреннего бенчмарка модели.

---

## 17. Связанные документы

- `portfolio/METHODOLOGY.md` — общий enrichment (4lapy-era, CH-first)  
- `portfolio/tsum/` — полный эталонный пакет ЦУМ  
- `skills-portable/skills/metrika/SKILL.md` — токены и counter map  
- `.cursor/rules/partner-visual-demo-cases.mdc` — всегда 5 кейсов с фото  
- `filter_pipeline/README.md` — следующий шаг: closed-set фильтры после продажи идеи  

---

*Версия playbook: 1.0 · 2026-07-21 · Эталон: TSUM site 203 · commit после появления этого файла*
