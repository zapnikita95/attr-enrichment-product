# 06. Портфолио кейсов

## Назначение

Единый реестр доказательств ценности для sales, PM, decks и `proposal_builder.py`.  
**Машиночитаемая версия:** [portfolio/cases.yaml](../portfolio/cases.yaml).

**Правило использования:** на внешних встречах — anonymized_name; partner_hint только internal.

---

## Сводная таблица (7 кейсов)

| ID | Вертикаль | Стрим | Headline метрика | site_id | Приоритет deck |
|----|-----------|-------|------------------|---------|----------------|
| pharmacy_vision | Аптека | Vision | NDCG +0.003, Class E +2.6pp | 6390 | ★★★ |
| jewelry_form | Ювелирка | Vision | Zero −33%, NDCG +9% | — | ★★★ |
| befree_fashion | Fashion | Vision | 1747 rows, 49% truly_new | 1967 | ★★★ |
| discount_ocr | Дискаунт | Vision | 11k SKU, 340 zero→result | — | ★★ |
| kids_8858 | Детские | Text | 180 vocab gaps, 95 attrs | 8858 | ★★ |
| grocery_text | Grocery | Text | 130 attrs in production | 221 | ★★ |
| petrovich_attrs_audit | Строительный | Audit | 42% шумных attrs | 519 | ★★★ (negative) |

---

## Кейс 1: Аптека (pharmacy_vision)

| Поле | Значение |
|------|----------|
| **Партнёр** | Ozerki (анонимизировано: «Аптечная сеть») |
| **site_id** | 6390 |
| **Стрим** | Vision — OCR упаковки, Original_name |
| **Атрибуты** | `Original_name`, `digi_attr_image` (OCR) |

**Метрики (post-impl eval):**

| Метрика | Δ | Интерпретация |
|---------|---|---------------|
| NDCG@20 | +0.003 | Улучшение ранжирования топ-20 |
| Precision@20 | +0.010 | Больше релевантных в топе |
| Class E (exact) | +2.6 п.п. | Точная выдача |
| Class I (irrelevant) | −2.2 п.п. | Меньше «не то» |
| Class S | −0.5 п.п. | — |
| Class C | +0.1 п.п. | — |

**Story (для deck):**  
Запрос «стельки» → в выдаче чай для сосудов. После OCR торгового названия с упаковки — ортопедические стельки в топе. **Class I снизился сильнее, чем прирост ndcg** — лучший UX-аргument для e-commerce.

**Proof:** user_screenshot, `ozerki_attribute_impact_data.json`  
**Slide:** internal #8, client #7

---

## Кейс 2: Ювелирка (jewelry_form)

| Поле | Значение |
|------|----------|
| **Стрим** | Vision — form, metal_color, digi_attr_pattern |
| **Масштаб** | Multi-SKU catalog |

**Метрики:**

| Метрика | Значение |
|---------|----------|
| Zero queries reduction | **−33%** |
| NDCG@20 avg increase | **+9%** |

**Story:** Покупатели ищут форму украшения («кольцо змея», «серьги череп») — в фиде только «изделие 585». Vision атрибут `form` закрыл zero-запросы без PIM.

**Slide:** internal #7, client #6 — headline метрика для C-level

---

## Кейс 3: Befree / Fashion (befree_fashion)

| Поле | Значение |
|------|----------|
| **site_id** | 1967 |
| **Стрим** | Vision — OCR, print_pattern |
| **Атрибуты** | `digi_attr_image`, `digi_attr_pattern`, `print_pattern` |

**Метрики:**

| Метрика | Значение |
|---------|----------|
| Dashboard rows uploaded | **1747** |
| SKU with truly_new lexicon | **49%** |

**Story:** Принт и надписи на одежде — главный gap fashion-поиска. Batch + Dashboard без IT Befree. Почти половина SKU получила слова, которых не было в YML.

**Proof:** befree_pattern_study, dashboard_sent.json  
**Slide:** internal #9, client #8

---

## Кейс 4: Дискаунт (discount_ocr)

| Поле | Значение |
|------|----------|
| **Стрим** | Vision — OCR упаковки |
| **Масштаб** | **11 000 SKU** |

**Метрики:**

| Метрика | Значение |
|---------|----------|
| sku_processed | 11 000 |
| zero_to_result_queries | 340 |

**Story:** Массовый OCR для discount-сети с бедными supplier-описаниями. Закрыты zero-запросы по брендам и составу с упаковки.

**Slide:** internal #10 (text/vision grid), client — optional appendix

---

## Кейс 5: Детский мир (kids_8858)

| Поле | Значение |
|------|----------|
| **site_id** | 8858 |
| **Стрим** | Text + LoRA |
| **Атрибуты** | age_group, material, character |

**Метрики:**

| Метрика | Значение |
|---------|----------|
| vocabulary_gaps_closed | 180 |
| attrs_extracted | 95 |

**Story:** Текстовый стрим с доменной дообученной моделью. Закрыты gaps в возрастных и тематических запросах (персонажи, материалы).

**Slide:** internal #10 (pair with grocery)

---

## Кейс 6: Grocery (grocery_text)

| Поле | Значение |
|------|----------|
| **site_id** | 221 |
| **Стрим** | Text extraction |
| **Масштаб** | **130 атрибутов** in production |

**Метрики:**

| Метрика | Значение |
|---------|----------|
| attrs_in_production | 130 |
| lexicon_gap_closure_pct | 35% |

**Story:** Извлечение из богатых supplier-описаний и params. Референс для mid-market text-first сделок.

---

## Кейс 7: Petrovich (petrovich_attrs_audit) — negative

| Поле | Значение |
|------|----------|
| **site_id** | 519 |
| **Тип** | Audit current_attrs (не enrichment) |

**Метрики:**

| Метрика | Значение |
|---------|----------|
| noisy_attrs_pct | 42% |
| duplicate_attrs | 18 |
| conflicting_values | 7 |

**Story:** Обратный кейс — плохие атрибуты **ухудшают** ранжирование. Сначала cleanup, потом enrichment. Доказывает зрелость: Studio audit до batch.

**Proof:** petrovich_519_qbr_presentation.html, current_attrs_audit  
**Slide:** internal #13 (slide-attrs style)

---

## Как proposal_builder выбирает кейсы

1. Загружает `portfolio/cases.yaml`
2. Исключает `type: negative` из partner proposal (кроме audit pitch)
3. Сортирует по `slide_priority` (1 = top)
4. Boost +10 к score если `vertical` совпадает с `--vertical`
5. Берёт top 3 → `{{CASES_HTML}}` в template

```powershell
py -3.13 tools/proposal_builder.py --partner "Ozerki" --site-id 6390 --mrr 150000 --vertical "Аптека" --output decks/generated/ozerki-proposal.html
```

---

## Матрица «какой кейс кому показывать»

| Вертикаль prospect | Primary case | Secondary |
|--------------------|--------------|-----------|
| Аптека / pharma | pharmacy_vision | grocery_text |
| Fashion | befree_fashion | jewelry_form |
| Jewelry | jewelry_form | befree_fashion |
| Discount | discount_ocr | grocery_text |
| Kids | kids_8858 | — |
| Grocery | grocery_text | kids_8858 |
| DIY / строительный | petrovich_attrs_audit | discount_ocr |

---

## Чеклист обновления портфолио

- [ ] Метрики с источником (JSON / screenshot / QBR)
- [ ] story ≤ 3 предложения для deck
- [ ] slide_priority актуален
- [ ] partner_hint не в client-facing materials
- [ ] YAML валиден (`yaml.safe_load`)

---

*Версия: 2026-Q3 · attr-enrichment-product*
