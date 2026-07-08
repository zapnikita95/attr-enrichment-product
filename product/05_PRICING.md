# 05. Ценообразование

## Назначение

Зафиксированная модель цены для sales, PM и защиты продукта. **Не менять в поле** без approval — использовать [pricing_calculator.html](../tools/pricing_calculator.html).

---

## Модель (зафиксированная)

| Тип | Формула | Когда применяем |
|-----|---------|-----------------|
| **Разовый batch** | `1 × MRR` | Первичная обработка всего / большого среза фида |
| **Регулярное обогащение** | `MRR × 5–10%` | Фид обновляется, новинки нужно обрабатывать |

**Принцип:** batch привязан к **месячному MRR поиска**, не к количеству SKU напрямую. SKU влияет на срок delivery, не на формулу (исключения — пилот).

---

## Правило выбора % recurring

| Новинок в неделю | % MRR | Обоснование |
|------------------|-------|-------------|
| ≤ 500 | **5%** | Низкий поток, минимальный ops |
| 501–2000 | **7.5%** | Средний поток, weekly delta |
| > 2000 | **10%** | Высокий поток, near-continuous pipeline |

Реализация в коде: `proposal_builder.py` → `recurring_pct()`.

---

## Примеры для deck и КП

| MRR | SKU | Новинок/нед | Batch (разовый) | Recurring/мес | % |
|-----|-----|-------------|-----------------|---------------|---|
| 30 000 ₽ | 15k | 200 | 30 000 ₽ | 1 500 ₽ | 5% |
| 50 000 ₽ | 40k | 1 000 | 50 000 ₽ | 5 000 ₽ | 10% |
| 150 000 ₽ | 80k | 800 | 150 000 ₽ | 11 250 ₽ | 7.5% |
| 500 000 ₽ | 120k | 3 000 | 500 000 ₽ | 50 000 ₽ | 10% |

**Калькулятор:** [tools/pricing_calculator.html](../tools/pricing_calculator.html) — интерактивный расчёт + формулировка для КП.

---

## Обоснование для клиента (talk track)

### Batch = 1 MRR

- Понятный чек, сопоставим с «месяцем поиска»
- Покрывает: GPU compute, analyst diagnostics, QA sample, одну заливку Dashboard
- Альтернатива партнёра: контент-команда × месяцы × FTE — дороже и медленнее

### Recurring 5–10%

- Дешевле повторного full batch каждые 6 месяцев
- Удерживает качество поиска на потоке новинок
- Прозрачная формула — нет сюрпризов в invoice

### Не включено в базовый MRR

- Compute-heavy опция (GPU, LLM inference)
- Партнёр платит за **измеримый** uplift, не за «фичу в коробке»
- Защищает margin базового search-as-a-service

---

## Границы и исключения (internal only)

| Правило | Значение | Кто approves |
|---------|----------|--------------|
| Минимальный чек batch | 30 000 ₽ (= 1 MRR при MRR=30k) | PM |
| Скидки на batch | Max −15% | PM + руководство |
| Пилот 5–10k SKU | **0.2× MRR** entry | PM (на защите) |
| Только recurring без batch | **Нет** — сначала batch или пилот | — |
| Audit/cleanup (Petrovich-style) | Отдельный T&M или fixed fee | PM |
| Custom attributes > 20 | Scope review, срок +1 нед | Eng |

**В калькуляторе скидки не показываем** — только list price.

---

## Что входит в batch (scope)

| Включено | Не включено |
|----------|-------------|
| Диагностика Studio (если не была) | Изменение PIM партнёра |
| Extraction на согласованный scope SKU/attrs | Ручная разметка всего каталога |
| QA выборки (~1%) + fix critical errors | Неограниченные итерации заливки |
| Заливка Dashboard (1 итерация) | SERP redesign |
| Post-impl eval report (базовый) | Legal / compliance audit |
| CSV export для audit партнёра | Обучение моделей под exclusive IP |

---

## FAQ pricing

**Почему не фикс за SKU?**  
MRR отражает strategic value партнёра для Diginetica. 100k SKU у mid-market и enterprise — разный retention risk и upsell potential.

**Можно ли только vision без text?**  
Да. Scope и цена не меняются — 1×MRR за согласованный batch (один или оба стрима в одном scope).

**Recurring обязателен?**  
Нет. Рекомендуем при > 200 новинок/неделю. Без recurring — риск деградации через 3–6 мес.

**Как считать MRR для формулы?**  
Актуальный MRR search contract на дату КП. При multi-site — site_id scope.

**Пилот потом зачтётся в batch?**  
Обсуждаемо: pilot 0.2×MRR может быть credit к full batch при конверсии в 90 дней.

**Валюта и НДС?**  
₽, как основной search contract. НДС — по шаблону Diginetica billing.

---

## Матрица переговоров

| Запрос клиента | Стандартный ответ | Escalation |
|----------------|-------------------|------------|
| −20% на batch | Пилот + post-impl proof | PM −15% max |
| Оплата по milestone | 50% sign / 50% upload OK | Finance |
| Fixed fee за SKU | Отказ, объяснить MRR model | — |
| Free POC full catalog | Диагностика free, batch paid | Sales lead |

---

## Связь с proposal_builder

Поля в generated deck:

```json
"pricing": {
  "mrr": 150000,
  "batch": 150000,
  "recurring_pct": 7.5,
  "recurring": 11250
}
```

---

## Связь с sales CRM

| CRM stage | Pricing artifact |
|-----------|------------------|
| Qualified (phase 0) | MRR known → rough batch orientir |
| Impact done (phase 2) | pricing_calculator screenshot |
| Proposal sent (phase 4) | partner-proposal.html + batch/recurring in quote |
| Signed (phase 5) | Exact batch + recurring in contract |
| Recurring live (phase 9) | % MRR auto from new_per_week tier |

---

*Версия: 2026-Q3 · attr-enrichment-product*
