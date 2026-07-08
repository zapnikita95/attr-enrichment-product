# 06. Портфолио кейсов

## Назначение

Единый реестр доказательств ценности для sales, PM и decks. Машиночитаемая версия: [portfolio/cases.yaml](../portfolio/cases.yaml).

---

## Сводная таблица

| ID | Вертикаль | Стрим | Headline метрика | Приоритет deck |
|----|-----------|-------|------------------|----------------|
| pharmacy_vision | Аптека | Vision | NDCG +0.003, Class E +2.6pp | ★★★ |
| jewelry_form | Ювелирка | Vision | Zero −33%, NDCG +9% | ★★★ |
| befree_fashion | Fashion | Vision | 1747 rows, 49% truly_new | ★★★ |
| discount_ocr | Дискаунт | Vision | 11k SKU OCR | ★★ |
| kids_8858 | Детские | Text | Vocabulary gaps | ★★ |
| grocery_text | Grocery | Text | 130 attrs | ★★ |
| petrovich_attrs_audit | Строительный | Audit | 42% шумных attrs | ★★★ (negative) |

---

## Кейс 1: Аптека (vision)

**Партнёр (анонимизировано):** аптечная сеть, site_id 6390.

**Атрибуты:** Original_name, OCR упаковки (`digi_attr_image`).

**Метрики:**

| Метрика | Δ |
|---------|---|
| NDCG@20 | +0.003 |
| Precision@20 | +0.010 |
| Class E | +2.6 п.п. |
| Class I | −2.2 п.п. |

**Story:** Запрос «стельки» → в выдаче чай для сосудов. После OCR с упаковки — корректные ортопедические стельки. Class I (нерелевантная выдача) снизился сильнее, чем прирост ndcg — лучший UX-аргумент.

---

## Кейс 2: Ювелирка (vision)

**Атрибуты:** form (змея, череп, сердце), metal_color.

**Метрики:**

- Нулевая выдача: **−33%**
- NDCG@20: **+9%** в среднем

**Story:** Покупатели ищут форму украшения словами, которых нет в фиде. Vision закрывает zero-запросы без изменения PIM.

---

## Кейс 3: Befree / Fashion (vision)

**site_id:** 1967.

**Атрибуты:** OCR надписей, print_pattern (`digi_attr_pattern`).

**Метрики:**

- **1747** строк залито в Dashboard
- **49%** SKU с truly_new лексикой (слова, которых не было в фиде)

**Story:** Принт и надписи на одежде — главный gap fashion-поиска. Batch + Dashboard без IT Befree.

---

## Кейс 4: Дискаунт (vision)

**Масштаб:** 11 000 SKU.

**Атрибуты:** OCR упаковки.

**Результат:** Массовое закрытие zero-запросов по брендам и составу из supplier-карточек с бедными описаниями.

---

## Кейс 5: Детский мир (8858, text)

**Стрим:** attributes_extraction + LoRA.

**Фокус:** age_group, character, material — vocabulary gaps в детской лексике.

---

## Кейс 6: Grocery (221, text)

**Масштаб:** 130 атрибутов в production.

**Стрим:** извлечение из богатых описаний и params.

---

## Кейс 7: Petrovich (519) — обратный кейс

**Тип:** audit current_attrs (не enrichment).

**Вывод:** 42% шумных атрибутов ухудшают поиск. Сначала cleanup, потом обогащение.

**Использование в sales:** «Мы не заливаем всё подряд — оцениваем в Studio до работ».

---

## Как использовать в КП

`proposal_builder.py` подбирает 2–3 кейса по `vertical` партнёра из `cases.yaml`.

---

*Версия: 2026-Q3*
