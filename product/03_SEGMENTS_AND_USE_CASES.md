# 03. Сегменты и use cases

## Назначение документа

Определить **кому** продаём, **какой стрим** рекомендуем и **какой motion** (enterprise retention vs new win). Используется на фазе 0 (квалификация) и фазе 3 (1-pager recommendation).

---

## Три сегмента

### A. Enterprise (действующий партнёр, MRR 500k–3M+)

| Параметр | Значение |
|----------|----------|
| **Боль** | Нет возможности менять фид; нужен retention и дифференциация |
| **Продукт** | Batch 1×MRR + recurring 5–10% |
| **Стрим** | Чаще vision (одежда, ювелирка, аптека) + text для grocery/pharma |
| **Процесс** | Studio current_attrs eval → pitch → batch → QBR-отчёт |
| **Decision maker** | Head of e-commerce + IT (Dashboard access) |
| **Sales cycle** | 4–8 недель (диагностика → КП → согласование → delivery) |
| **Примеры** | Befree (1967), Ozerki (6390), Petrovich (519 — attrs audit), Fix Price (1976) |

**Типичный use case:**

1. Партнёр видит рост нулевых запросов по визуальным терминам в QBR поиска
2. Studio показывает lexicon gap 40%+ и product_reach 80k SKU
3. Pitch на retention-встрече: batch vision на 100k SKU, 1×MRR
4. Заливка в Dashboard за 1–3 дня (TOTP от партнёра)
5. QBR через 4 недели: NDCG, zero%, Class E — Petrovich-style deck

**KPI успеха сделки:** post-impl zero ↓ или Class E ↑; подписан recurring; renewal search MRR.

### B. Mid-market (MRR 100–500k)

| Параметр | Значение |
|----------|----------|
| **Боль** | Растущий каталог, слабые описания поставщиков |
| **Продукт** | Batch + опциональный recurring |
| **Стрим** | Text extraction чаще; vision для fashion/beauty |
| **Decision maker** | E-commerce manager (меньше IT friction) |
| **Sales cycle** | 2–4 недели |
| **Примеры** | Zolla, Noone, Parfum Lider |

**Типичный use case:**

1. 40k SKU, богатые supplier-описания, но неструктурированные
2. Text extraction на 50–130 атрибутов (референс: grocery 221)
3. Пилот на 1–2 категории (5–10k SKU) → NDCG до/после
4. Масштаб на весь каталог; recurring если > 500 новинок/нед

**KPI успеха:** закрытие vocabulary gaps; batch окупается vs найм контент-редактора.

### C. New partner (pre-sales / A/B)

| Параметр | Значение |
|----------|----------|
| **Боль** | Нужно показать ценность поиска до контракта |
| **Продукт** | **Диагностика бесплатно** (Studio) → платный пилот batch (0.2×MRR обсуждаемо) |
| **Стрим** | Тот, где closure forecast выше (Studio step 7) |
| **Decision maker** | C-level + procurement |
| **Sales cycle** | 2–6 недель до пилота |
| **KPI успеха** | Lexicon gap closure % + demo deck с **их** цифрами |

**Типичный use case:**

1. Pre-sales: загрузка фида в Studio (с согласия)
2. Impact run → персональный `partner-proposal.html` через proposal_builder
3. Пилот 5–10k SKU (0.2×MRR entry) → A/B или demo environment
4. Конверсия в полный search + batch контракт

---

## Decision tree: какой стрим

```
START: Есть YML/XML фид?
  NO → No-go (фаза 0)

Есть фото + gap в визуальных терминах (Studio step 3–4)?
  YES → image_description (vision)
  NO  → ↓

Есть богатые описания + gap в тексте?
  YES → attributes_extraction (text)
  NO  → ↓

Оба gap (vision + text)?
  YES → Vision first (быстрее wow на demo), потом text batch

Нет gap, но шумные current_attrs (>30% noise)?
  YES → Cleanup audit (кейс Petrovich), НЕ enrichment batch

Нет gap и чистый фид?
  YES → Не продаём enrichment; предложить search tuning / synonyms
```

**Правило PM:** vision first для demo и QBR wow; text first для grocery/pharma с длинными descriptions.

---

## Use cases по вертикалям

| Вертикаль | Стрим | Ключевые атрибуты | Кейс ID | Headline |
|-----------|-------|-------------------|---------|----------|
| Аптека | Vision | OCR упаковки, Original_name | pharmacy_vision | Class E +2.6pp |
| Ювелирка | Vision | form, metal_color | jewelry_form | Zero −33% |
| Fashion | Vision | OCR, print_pattern | befree_fashion | 49% truly_new |
| Дискаунт | Vision | OCR | discount_ocr | 11k SKU |
| Детские товары | Text | age, character, material | kids_8858 | 180 vocab gaps |
| Grocery | Text | 130 attrs из описаний | grocery_text | 130 in prod |
| Строительный | Audit | current_attrs cleanup | petrovich_attrs_audit | 42% noise |

Полный реестр: [06_PORTFOLIO.md](06_PORTFOLIO.md), [portfolio/cases.yaml](../portfolio/cases.yaml).

---

## Personas (кратко)

| Persona | Что важно | Как говорить |
|---------|-----------|--------------|
| **Head of e-commerce** | Конверсия, нули, конкуренты | Zero rank-list, story-кейсы |
| **IT / интеграции** | Без изменения PIM, безопасность | Dashboard API, on-prem, TOTP |
| **Контент / MDM** | Не добавлять работу команде | «Мы batch, вы QA 1% выборки» |
| **CFO / procurement** | Цена vs альтернатива | 1×MRR vs FTE; recurring прозрачен |
| **Наш AM / sales** | Upsell, retention | Studio JSON → proposal за 1 день |

---

## Квалификация сегмента (scorecard)

| Критерий | 0 баллов | 1 балл | 2 балла |
|----------|----------|--------|---------|
| MRR | < 30k | 30–100k | > 100k |
| Lexicon gap | < 10% | 10–30% | > 30% |
| Фид + фото | Нет | Частично | Полный YML + фото |
| Dashboard attrs | Отказ | «Обсудим» | Согласны |
| IT bandwidth | Блокируют всё | Медленно | TOTP готовы |

**Go:** ≥ 6 баллов. **Пилот only:** 4–5. **No-go:** ≤ 3.

Чеклист фазы 0: [04_SALES_PROCESS.md](04_SALES_PROCESS.md).

---

## Сегмент × pricing (ориентир)

| Сегмент | Batch | Recurring | Скидки |
|---------|-------|-----------|--------|
| Enterprise | 1×MRR | 5–10% | Только approval |
| Mid | 1×MRR | Опционально 5–7.5% | Пилот 0.2×MRR |
| New | 0.2×MRR пилот | После полного контракта | Входит в win package |

---

## Анти-пatterns (не путать сегменты)

| Ошибка | Почему плохо | Правильно |
|--------|--------------|-----------|
| Vision batch на grocery без фото-gap | Дорого, мало uplift | Text extraction |
| Text на jewelry form queries | Не закроет zero | Vision form |
| Enrichment до audit Petrovich-style | Шум ухудшит поиск | Cleanup first |
| Бесплатный full batch для new | Сжигает GPU | Платный пилот 5–10k SKU |

---

## Связанные документы

- [04_SALES_PROCESS.md](04_SALES_PROCESS.md) — фазы 0–9 по сегментам
- [05_PRICING.md](05_PRICING.md) — цены и исключения
- [tools/proposal_builder.py](../tools/proposal_builder.py) — кейсы по vertical

---

*Версия: 2026-Q3 · attr-enrichment-product*
