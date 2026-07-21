# Attribute Enrichment — Переиспользуемая методология

> **Owner:** Hermes AI + Analyst  
> **Версия:** 2.0 · 2026-07-13  
> **Назначение:** ОДИН раз записать, откуда берутся данные, какие скрипты, как считать выручку. Для **любого** партнёра (не только 4lapy).

---

## Vision attributes (продажа идеи с фото + ₽)

**Полный playbook (эталон ЦУМ, 2026-07):**  
→ [`VISION_ATTR_PARTNER_PLAYBOOK.md`](./VISION_ATTR_PARTNER_PLAYBOOK.md)

Там по шагам: фид inventory → CH запросы → OpenRouter vision → KEEP/REJECT → Diginetica RESERVE API → **Яндекс.Метрика CVR** → Δ₽ → **5 кейсов с картинками**.  
Пакет артефактов: `portfolio/tsum/`.

---

## 0. Быстрый старт для нового партнёра

1. Получить `site_id`, `apiKey` (Diginetica) из дашборда/API
2. Скопировать YML-фид: `cp ~/Downloads/yml-feed.{site_id}.xml portfolio/yml-feed.xml`
3. Обновить `ch_config.py`: `site_id`, возможно host/user/password CH
4. Запустить пайплайн:
   ```bash
   python yml_gap_analyzer.py          # Шаг 1: YML gap-анализ (7 сек)
   python reserve_analyzer.py          # Шаг 2: Reserve через Diginetica API (50k запросов)
   python dedup_and_urls.py            # Шаг 3: Дедупликация
   python final_analysis.py            # Шаг 4: Сводка
   ```
5. HTML-отчёт → `portfolio/{partner}-gap-analysis.html` (через `delegate_task specialist=frontend_heavy`)
6. После аппрува: `attribute_extractor.py` (описания → LLM) + `vision_enrichment.py` (фото)

---

## 1. Источники данных

### 1.1 ClickHouse (CH) — поведенческие метрики

| Что | Таблица / источник | Как получить |
|-----|-------------------|-------------|
| Конверсия (сессионная) | `sessions.agg_sessions` | `fetch_ch_conversion_v2.py` |
| Средний чек | `sessions.agg_sessions` | Тот же скрипт |
| Zero rate (частотный) | `sessions.zero_query` | Агрегат по site_id |
| Топ запросов | `sessions.searches` | `LIMIT 50000` (НЕ full scan) |
| Gap-запросы | Закэшированный JSON | `portfolio/gap-queries.json` |

**Конфиг:** `ch_config.py` в корне проекта.  
**⚠️ `isZeroQuery` — строка `'true'`/`'false'`, НЕ boolean.**  
**⚠️ Full scan (800M строк) падает с 500.**  
**⚠️ HTTPS 8443, verify=False.**

### 1.2 Diginetica API — статус запросов (reserve/normal/zero)

```
GET https://sort.diginetica.net/search
  ?st=<query>
  &apiKey=<KEY>
  &strategy=advanced_xname,zero_queries
  &size=0
```

| Поле ответа | Значение | Классификация |
|------------|----------|--------------|
| `totalHits = 0` | Товаров нет | **ZERO** |
| `totalHits > 0 && zeroQueries = true` | Товары есть, но не ищутся | **RESERVE** — основной фокус |
| `zeroQueries = false` | Нормальная выдача | **NORMAL** — исключить из gap |

**⚠️ Однопоточный! ThreadPool кладёт API. Без VPN для скорости (30-50 rps).**

### 1.3 YML-фид — источник истины о товарах

Файл: `portfolio/yml-feed.xml` (копируется из Downloads).  
Содержит: `<param name="...">` (18/товар), `<name>`, `<url>`, `<picture>`.

**ВСЕГДА проверять:** есть ли атрибут в YML перед тем как объявлять его новым.  
**YML-ключи (4lapy):** Артикул, Назначение, Материал, Тип корма, Вкус корма, Вес/фасовка, Возраст, Порода, Размер, Страна, Бренд, Форма выпуска, etc. (всего ~32 уникальных имени параметров).

---

## 2. Типы запросов и формула выручки

### 2.1 Классификация по Diginetica

```
Все запросы
  ├─ ZERO (totalHits=0)          — товаров нет в индексе. Добавление атрибутов НЕ поможет (нужны новые товары).
  ├─ RESERVE (hits>0, zero=true)  — товары ЕСТЬ, но не находятся. ★ ОСНОВНОЙ ФОКУС.
  └─ NORMAL (zero=false)          — выдача работает. Можно улучшить точность/ранжирование.
```

### 2.2 Дельта-методология (ПОЧЕМУ RESERVE → точный даёт разный прирост)

Это **критически важный нюанс**, который пользователь указал:

| Переход | Базовая конверсия | Прирост | Почему |
|---------|-------------------|---------|--------|
| **ZERO → RESERVE** | 0% (нет товаров) | Максимальный | Появляется сама возможность купить |
| **RESERVE → точный** | ~1.5-2% (запасная выдача) | Средний | Запасная выдача уже что-то показывает, но плохо |
| **NORMAL → точный** | ~3.15% (норм. выдача) | Минимальный | Выдача уже хорошая, улучшаем точность |

**Формула дельты:**

```
ΔВыручка = частота_запроса × (новая_конверсия − текущая_конверсия) × средний_чек

Где:
- ZERO → RESERVE:  текущая = 0%,       новая = 1.5-2% (консервативно 50% от нормы)
- RESERVE → точный: текущая = 1.5-2%,  новая = 3.15% (полная конверсия)
- NORMAL → точный:  текущая = 3.15%,   новая = 3.5-4% (улучшение точности)
```

**Пример (4lapy):**
```
Запрос «корм urinary»: 84 поиска/мес, RESERVE (hits>0, zero=true)
Текущая: 84 × 0.02 × 2117 = 3,557 ₽/мес (запасная выдача)
Новая:   84 × 0.0315 × 2117 = 5,602 ₽/мес (точная выдача)
Δ = +2,045 ₽/мес на ОДНОМ запросе
```

**⚠️ Консервативный коэффициент 50%:** для новых товаров в выдаче берём половину от полной конверсии, т.к. товар появляется не на первой позиции.

### 2.3 Общая формула (для отчёта)

```
Выручка = Σ(частота_запроса_в_мес) × КОНВЕРСИЯ_ИЗ_CH × СРЕДНИЙ_ЧЕК_ИЗ_CH

Реальные метрики 4lapy (90 дней, 13.07.2026):
- Конверсия (сессионная): 3.15%
- Средний чек: 2,117 ₽
- Выручка с поиска: 35,576,925 ₽ / 90д = 11.9M ₽/мес
```

---

## 3. Скрипты и пайплайн

### 3.1 Основной конвейер (для любого партнёра)

| # | Скрипт | Вход | Выход | Время |
|---|--------|------|-------|-------|
| 1 | `yml_gap_analyzer.py` | `portfolio/yml-feed.xml` | `portfolio/yml-gap-analysis.json` | 7 сек |
| 2 | `reserve_analyzer.py` | `portfolio/top-50k-queries-ch.json` | `portfolio/reserve-queries.json` | 1-2 часа |
| 3 | `dedup_and_urls.py` | `portfolio/reserve-queries.json` | `portfolio/all-queries-urls.json` | 5 сек |
| 4 | `final_analysis.py` | reserve + gap JSON'ы | `portfolio/final-analysis.json` | 1 сек |
| 5 | `fetch_ch_conversion_v2.py` | CH агрегаты | Метрики в консоль | 10 сек |

### 3.2 Извлечение атрибутов (после одобрения gap-анализа)

| # | Скрипт | Что делает |
|---|--------|-----------|
| 6 | `frontend_scraper.py` | Скрейпинг описаний с карточек (только если YML недостаточно) |
| 7 | `attribute_extractor.py` | LLM-извлечение атрибутов → gap-matching → выручка |
| 8 | `vision_enrichment.py` | Vision-модели: атрибуты с фото (новая лексика) |

### 3.3 Верификация (перед отчётом)

```bash
python reverify_gap_queries.py  # Перепроверить статус gap-запросов через Diginetica
```

---

## 4. Как собирать метрики из ClickHouse

### 4.1 Конверсия + средний чек

```bash
python fetch_ch_conversion_v2.py
```

**Что считает:** сессии с поиском → заказы → конверсия → средний чек.  
**Методология:** `sessions.agg_sessions`, дедуп по `sessionId` + `max(searches/autocompleteClicks)`.

### 4.2 Zero rate (частотно-взвешенный)

```sql
SELECT SUM(zero_searches) / SUM(total_searches) * 100
FROM sessions.zero_query
WHERE site_id = <site_id>
```

### 4.3 Топ запросов (для reserve-анализа)

```sql
SELECT searchTerm, count() AS cnt
FROM sessions.searches
WHERE siteId = <site_id>
  AND date >= today() - 90
GROUP BY searchTerm
ORDER BY cnt DESC
LIMIT 50000
```

---

## 5. HTML-отчёт (deliverable)

### 5.1 Структура

1. Текущие показатели (CH)
2. Gap-анализ: YML (token matching)
3. Атрибуты из описаний (LLM extraction)
4. Атрибуты с фото (Vision — новая лексика)
5. Reserve + Zero (Diginetica)
6. Сводка: доход (таблица)
7. План действий
8. Методология расчёта
9. Инструменты

### 5.2 Правила

- **Формат:** HTML, НЕ PDF/PPTX.
- **Шаблон:** `decks/templates/partner-proposal.template.html`
- **Генерация:** `delegate_task specialist=frontend_heavy` (gemma4:26b)
- **Дизайн:** фиксированный CSS из `portfolio/4lapy-gap-analysis.html` (v1 эталон)
- **Проверка:** открыть в браузере, НЕ запускать verification-скрипты до аппрува пользователя

### 5.3 Данные для делегации

При передаче сабагенту — **структурированная таблица** (не проза):

```
RESERVE-запросы (19 шт):
| Запрос | Поисков/мес | totalHits | Атрибут | Тип (search/filter) | Δ ₽/мес |
|--------|------------|-----------|---------|---------------------|----------|
| ...    | ...        | ...       | ...     | ...                 | ...      |
```

---

## 6. Применение к новому партнёру

### 6.1 Что заменить

| Параметр | Где | Пример (4lapy) |
|----------|-----|----------------|
| `site_id` | `ch_config.py`, все SQL-запросы | 8267 |
| `apiKey` | `reserve_analyzer.py`, все URL | 5F4132P11T |
| YML-фид | `portfolio/yml-feed.xml` | 8267.global.xml |
| CH host/user/pass | `ch_config.py` | rc1a-... |

### 6.2 Что сохраняется

- Все скрипты (параметризованы)
- Методология расчёта (формулы универсальны)
- HTML-шаблон (меняется только логотип/цвета)
- Пайплайн делегирования

### 6.3 Оценка до запуска (pre-sales)

```
Берём:
1. YML-фид → yml_gap_analyzer.py → 41.9% gap-покрытия (для 4lapy)
2. 50k запросов → reserve_analyzer.py → 32% reserve (для 4lapy)
3. Метрики CH (конверсия, чек, zero rate)
4. Формула: reserve_поиски × конверсия × чек × 0.5 (консервативно)

Результат: прогноз доп. выручки в ₽/мес.
```

---

## 7. Чеклист «перед показом партнёру»

- [ ] Все цифры из CH (не хардкод)
- [ ] RESERVE запросы верифицированы через Diginetica
- [ ] NORMAL исключены из gap (не «покрытые gap»)
- [ ] Атрибуты НОВЫЕ (не дубли YML)
- [ ] Связка: атрибут → слово в запросе → запрос
- [ ] Для фото: примеры запросов с близкой лексикой из CH
- [ ] Формула выручки с консервативным коэффициентом (50%)
- [ ] HTML открывается в браузере
- [ ] Источник данных указан (CH, период)
- [ ] Конверсия = сессионная, не поисковая

---

## 8. Где что лежит

| Ресурс | Путь |
|--------|------|
| CH конфиг | `ch_config.py` |
| YML-фид | `portfolio/yml-feed.xml` |
| Gap-запросы (кэш) | `portfolio/gap-queries.json` |
| Reserve-результаты | `portfolio/reserve-queries.json` |
| Дедупликация | `portfolio/all-queries-urls.json` |
| Сводный анализ | `portfolio/final-analysis.json` |
| HTML-отчёт | `portfolio/{partner}-gap-analysis.html` |
| CH-метрики | `portfolio/gap-conversion-ch.json` |
| Прайсинг | `tools/pricing_calculator.html` |
| Шаблон HTML | `decks/templates/partner-proposal.template.html` |
| Скилл пайплайна | `skills/mlops/enrichment-4lapy/SKILL.md` |
| Скилл моделей | `skills/mlops/local-model-first/SKILL.md` |

---

## 9. Частые ошибки

| Ошибка | Как правильно |
|--------|--------------|
| Хардкод-конверсия 3.5% | Всегда `fetch_ch_conversion_v2.py` |
| NORMAL в gap-отчёте | Только RESERVE (zeroQueries=true) |
| «Стало точнее» для reserve | «Новые товары появятся в выдаче» |
| ThreadPool в reserve_analyzer | Однопоточный for-цикл |
| Full scan CH (800M) | LIMIT 50000 |
| gemma4:12b для HTML | Только gemma4:26b через frontend_heavy |
| Backslash в путях | Только forward slash (`C:/Users/...`) |
| Verification-вывод вместо итогов | Структура: заголовок → цифры → таблица → что дальше |

---

*Версия: 2.0 · 2026-07-13 · Переиспользуемая для любого партнёра*