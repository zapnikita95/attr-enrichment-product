# 03. Сегменты и use cases

## Три сегмента

### A. Enterprise (действующий партнёр, MRR 500k–3M+)

| Параметр | Значение |
|----------|----------|
| **Боль** | Нет возможности менять фид; нужен retention и дифференциация |
| **Продукт** | Batch 1×MRR + recurring 5–10% |
| **Стрим** | Чаще vision (одежда, ювелирка, аптека) + text для grocery/pharma |
| **Процесс** | Studio current_attrs eval → pitch → batch → QBR-отчёт |
| **Примеры** | Befree (1967), Ozerki (6390), Petrovich (519 — attrs audit), Fix Price (1976) |

**Типичный use case:** партнёр видит рост нулевых запросов по визуальным терминам; Studio показывает lexicon gap 40%+; batch vision на 100k SKU; заливка в Dashboard; QBR через 4 недели.

### B. Mid-market (MRR 100–500k)

| Параметр | Значение |
|----------|----------|
| **Боль** | Растущий каталог, слабые описания поставщиков |
| **Продукт** | Batch + опциональный recurring |
| **Стрим** | Text extraction чаще; vision для fashion/beauty |
| **Примеры** | Zolla, Noone, Parfum Lider |

**Типичный use case:** 40k SKU, богатые supplier-описания, но неструктурированные; text extraction на 130 атрибутов; пилот на категории → масштаб.

### C. New partner (pre-sales / A/B)

| Параметр | Значение |
|----------|----------|
| **Боль** | Нужно показать ценность поиска до контракта |
| **Продукт** | **Диагностика бесплатно** (Studio) → платный пилот batch (0.2×MRR обсуждаемо) |
| **Стрим** | Тот, где closure forecast выше |
| **KPI успеха** | Lexicon gap closure % + demo deck с их цифрами |

---

## Decision tree: какой стрим

```
Есть фото + gap в визуальных терминах?
  → image_description (vision)

Есть богатые описания + gap в тексте?
  → attributes_extraction (text)

Оба gap?
  → Vision first (быстрее wow), потом text

Нет gap, но шумные current_attrs?
  → Cleanup audit (кейс Petrovich), не enrichment

Нет gap и чистый фид?
  → Не продаём; предложить другие опции поиска
```

---

## Use cases по вертикалям

| Вертикаль | Стрим | Атрибуты | Кейс |
|-----------|-------|----------|------|
| Аптека | Vision | OCR упаковки, Original_name | pharmacy_vision |
| Ювелирка | Vision | form, metal_color | jewelry_form |
| Fashion | Vision | OCR, print_pattern | befree_fashion |
| Дискаунт | Vision | OCR | discount_ocr |
| Детские товары | Text | age, character, material | kids_8858 |
| Grocery | Text | 130 attrs из описаний | grocery_text |
| Строительный | Audit | current_attrs cleanup | petrovich_attrs_audit |

Полный список: [06_PORTFOLIO.md](06_PORTFOLIO.md), [portfolio/cases.yaml](../portfolio/cases.yaml).

---

## Квалификация сегмента (быстрый чеклист)

- [ ] MRR ≥ 30k (иначе только пилот / отказ)
- [ ] site_id известен
- [ ] Есть YML/XML фид
- [ ] Вертикаль с визуальным или текстовым gap
- [ ] Партнёр согласен на Dashboard custom attrs

---

## Связанные документы

- [04_SALES_PROCESS.md](04_SALES_PROCESS.md) — фазы 0–9
- [05_PRICING.md](05_PRICING.md) — цены по сегментам

---

*Версия: 2026-Q3*
