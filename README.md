# Обогащение каталога для поиска

Единый B2B-продукт Diginetica: **оценка → извлечение атрибутов → заливка в Dashboard → метрики**.

Три репозитория — один процесс, одна цена, одни decks.

---

## Быстрый старт

**Двойной клик:** `start.bat` — откроет защиту продукта и калькулятор цены в браузере.

Или вручную:

| Что открыть | Путь |
|-------------|------|
| Защита продукта (18 слайдов) | [decks/internal-defense.html](decks/internal-defense.html) |
| Клиентский обзор (14 слайдов) | [decks/client-overview.html](decks/client-overview.html) |
| Калькулятор цены | [tools/pricing_calculator.html](tools/pricing_calculator.html) |

Навигация в decks: **стрелки**, **пробел**, **точки внизу**.

---

## Карта трёх репозиториев

| Репозиторий | Роль | Порт |
|-------------|------|------|
| [attr-impact-studio](https://github.com/zapnikita95/attr-impact-studio) | Диагностика, NDCG, impact forecast | 5050 |
| [attributes_extraction-main](https://github.com/zapnikita95/attributes_extraction) | Текстовый стрим | 8501 |
| [image_description-main](https://github.com/zapnikita95/image_description) | Vision-стрим (OCR, узор, форма) | 7860 |

**Этот пакет** (`attr-enrichment-product`) — product hub: документация, decks, pricing. Код трёх репо не дублируем.

---

## Документация (читать по порядку)

| # | Файл | Зачем |
|---|------|-------|
| 01 | [product/01_POSITIONING.md](product/01_POSITIONING.md) | Что продаём за 5 минут |
| 02 | [product/02_VALUE_AND_ROI.md](product/02_VALUE_AND_ROI.md) | Ценность, формулы, возражения |
| 03 | [product/03_SEGMENTS_AND_USE_CASES.md](product/03_SEGMENTS_AND_USE_CASES.md) | Enterprise / Mid / New |
| 04 | [product/04_SALES_PROCESS.md](product/04_SALES_PROCESS.md) | Фазы 0–9 |
| 05 | [product/05_PRICING.md](product/05_PRICING.md) | 1×MRR + 5–10% |
| 06 | [product/06_PORTFOLIO.md](product/06_PORTFOLIO.md) | Кейсы с метриками |
| 07 | [product/07_METRICS_PLAYBOOK.md](product/07_METRICS_PLAYBOOK.md) | NDCG, zero, Class E |
| 08 | [product/08_TECH_ARCHITECTURE.md](product/08_TECH_ARCHITECTURE.md) | Data flow |
| 09 | [product/09_INTERNAL_DEFENSE.md](product/09_INTERNAL_DEFENSE.md) | Сценарий защиты |
| 10 | [product/10_DECK_SPEC.md](product/10_DECK_SPEC.md) | Спецификация слайдов |

---

## Инструменты

### Калькулятор

`tools/pricing_calculator.html` — MRR, SKU, новинок/нед → batch + recurring.

### Proposal builder

```powershell
py -3.13 tools/proposal_builder.py ^
  --partner "Ozerki" ^
  --site-id 6390 ^
  --mrr 150000 ^
  --vertical "Аптека" ^
  --new-per-week 400 ^
  --impact-json "C:\path\to\ozerki_attribute_impact_data.json" ^
  --output decks/generated/ozerki-proposal.html
```

Требует: `pip install pyyaml`

### Пересборка decks

```powershell
py -3.13 tools/generate_decks.py
```

---

## Структура папок

```
attr-enrichment-product/
├── README.md
├── start.bat
├── product/           # 10 MD-документов
├── portfolio/
│   ├── cases.yaml
│   └── assets/
├── decks/
│   ├── engine/        # qbr-deck.css, qbr-deck.js
│   ├── data/          # product-default.json
│   ├── templates/
│   ├── generated/
│   ├── internal-defense.html
│   └── client-overview.html
└── tools/
    ├── pricing_calculator.html
    ├── proposal_builder.py
    └── generate_decks.py
```

---

## Pricing (кратко)

- **Batch:** `1 × MRR`
- **Recurring:** `5%` (≤500 нов./нед) · `7.5%` (501–2000) · `10%` (>2000)

---

## Критерии готовности

- [x] internal-defense.html — 18 слайдов, Petrovich style
- [x] client-overview.html — 14 слайдов
- [x] 10 product/*.md
- [x] cases.yaml — 7 кейсов
- [x] pricing_calculator.html
- [x] proposal_builder.py

---

*2026-Q3 · Diginetica Search*
