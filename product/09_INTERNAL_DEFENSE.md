# 09. Внутренняя защита продукта

## Назначение

Сценарий презентации **30–45 минут** для руководства и коллег: проблема → решение → доказательства → pricing → ask.  
**Deck:** [decks/internal-defense.html](../decks/internal-defense.html) (18 слайдов).

**Подготовка:** открыть deck на проекторе, иметь pricing_calculator на втором экране, cases.yaml под рукой.

---

## Тайминг по блокам

| Блок | Время | Слайды | Ключевой тезис |
|------|-------|--------|----------------|
| Проблема | 5 мин | 1–2 | Enterprise не может менять фид 6–18 мес |
| Решение | 5 мин | 3–5 | 2 стрима + Studio, без PIM |
| Ценность | 10 мин | 6–9 | Кейсы с цифрами (jewelry, pharmacy, befree) |
| Как продаём | 5 мин | 10–12 | Процесс + pricing 1×MRR |
| Портфолио / tech | 5 мин | 13–15 | Petrovich audit + segments |
| Риски | 5 мин | 16–17 | Честно: прогноз ≠ CTR |
| Ask | 5 мин | 18 | Утвердить pricing, analyst FTE |

---

## Скрипт по слайдам (speaker notes)

### Слайд 1 — Cover (1 мин)

«Обогащение каталога для поиска — единый B2B-продукт поверх трёх зрелых инструментов. Мы не меняем PIM партнёра, заливаем custom attributes в Dashboard и измеряем uplift.»

### Слайд 2 — Проблема (4 мин)

Три боли — по одной минуте + пример:

1. **Нули:** «кольцо змея» → 0 SKU  
2. **IT-очередь:** новый атрибут в YML = 6–18 месяцев  
3. **Визуал:** принт на фото, в фиде «хлопок 100%»

«Это не проблема поиска как алгоритма — это проблема **индекса**. Мы её решаем.»

### Слайд 3 — Решение (3 мин)

Два стрима: text (8501) + vision (7860). Studio (5050) **до** работ — прогноз ROI. Замкнутый цикл до QBR.

### Слайд 4 — Ценность (2 мин)

Четыре goal-cards: zero −33%, ndcg +9%, Class E +2.6pp, 49% truly_new. «Все цифры из production кейсов, не mock.»

### Слайд 5 — Процесс (2 мин)

Studio → Extract → Dashboard → Metrics. «Повторяемый playbook, фазы 0–9 в product/04.»

### Слайд 6 — Метрики portfolio (2 мин)

Усреднённые ориентиры + sparklines. Оговорка: малый ndcg delta на высоком baseline — норма.

### Слайды 7–9 — Кейсы (6 мин)

- **7 Jewelry:** zero −33% — headline для CEO  
- **8 Pharmacy:** Class E/I — story «стельки vs чай»  
- **9 Befree:** 1747 rows, 49% — enterprise retention proof

### Слайд 10 — Text cases (2 мин)

8858 kids + grocery 130 attrs — text stream works, not only vision.

### Слайд 11 — Studio (2 мин)

Wizard 7 шагов — бесплатная диагностика для qualified partners.

### Слайд 12 — Архитектура (2 мин)

3 репо, не дублируем код. Product hub = docs + decks.

### Слайд 13 — Enterprise / PIM (3 мин)

Petrovich style: 42% noisy attrs. «Мы не заливаем всё подряд.»

### Слайд 14 — Pricing (3 мин)

1×MRR batch + 5–10% recurring. Примеры 30k / 50k / 500k. Калькулятор live demo.

### Слайд 15 — Фазы 0–9 (2 мин)

Sales process repeatable — analyst + eng roles clear.

### Слайд 16 — Сегменты (2 мин)

Enterprise / Mid / New — три motion.

### Слайд 17 — Риски (3 мин)

Прогноз ≠ CTR → пилот. GPU → queue. TOTP → UI 8766. Три UI → product hub.

### Слайд 18 — Ask (5 мин)

См. раздел Ask ниже. Pause for questions.

---

## Ask к руководству

1. **Утвердить pricing:** batch = 1×MRR, recurring = 5–10% (без скидок в калькуляторе)
2. **Выделить analyst** 0.25–0.5 FTE на Studio-диагностику активных партнёров
3. **Разрешить пилот 0.2×MRR** для new partners (опционально, PM approval)
4. **Не включать в базовый MRR** — отдельная строка в КП search
5. **Green-light** 2 demo proposals (Ozerki, Befree) для sales enablement

---

## FAQ для руководства

### Почему не включить в базовый MRR?

Compute-heavy (GPU, LLM, analyst). 1 MRR за batch покрывает затраты и даёт upsell без размывания margin базового поиска. Enterprise понимают «опция за 1 месяц поиска».

### Кто делает?

| Роль | FTE orientir | Задачи |
|------|--------------|--------|
| Analyst | 0.25–0.5 | Studio, метрики, QBR |
| Eng | 0.25 per active batch | Extraction, upload |
| Sales + PM | Existing | Квалификация, КП |

### Какой margin?

On-prem Ollama — нет OpenAI API bills. COGS: GPU amortization, analyst hours, eng delivery. Pricing 1×MRR designed to cover batch COGS + margin.

### Конкуренты?

| Альтернатива | Слабость |
|--------------|----------|
| Ручная разметка | 6–18 мес, no search eval |
| SaaS PIM enrichment | Data leak, no Dashboard path |
| ChatGPT in-house | No scale, no feed collision |

### Почему три инструмента?

Исторически три зрелых репо в production. Product hub даёт единый narrative **без** risky refactor. Phase 2 (future): unified portal.

### Сколько сделок в pipeline?

7 вертикалей в portfolio, 3 сегмента. Target: 2 enterprise batch + 3 pilots per quarter (adjust at defense).

---

## Риски (честно)

| Риск | Impact | Митигация | Owner |
|------|--------|-----------|-------|
| Прогноз Studio ≠ CTR | Medium | Пилот 5–10k, NDCG proof | Analyst |
| Vision quality ∝ photo | Medium | Phase1, QA 1% | Eng |
| TOTP friction | Low | UI :8766, partner playbook | Sales |
| Малый ndcg на слайде | Low | Pair Class I + story | PM |
| Noisy current_attrs | High | Audit first (Petrovich) | Analyst |
| GPU bottleneck | Medium | ollama-queue-proxy | Eng |
| 3 UI confusion | Low | README + start.bat | PM |

---

## Аргументы «за»

1. **Retention:** enterprise не уйдёт к «поиск + enrichment» конкуренту  
2. **Differentiation:** замкнутый цикл оценка → заливка → метрики — редко на рынке  
3. **Доказательства:** 7 кейсов, real metrics, HTML decks ready  
4. **Понятный чек:** 1×MRR — sales не строит custom калькулятор  
5. **Low capex:** используем существующие 3 repos  

---

## Аргументы «против» (и ответы)

| Возражение коллег | Ответ |
|-------------------|-------|
| «Мало сделок» | 7 verticals × 3 segments; start with 2 enterprise accounts |
| «Долго delivery» | 2–4 нед vs 6–18 мес PIM — competitive |
| «Нужен PM» | Этот пакет = PM kit готов |
| «Support burden» | Recurring scoped 5–10%; QA 1% only |
| «Legal on data» | On-prem, partner TOTP control |

---

## После защиты — next steps

- [ ] Pricing approved in writing  
- [ ] Analyst allocation confirmed  
- [ ] Schedule rehearsal with sales (client-overview.html)  
- [ ] First qualified partner → Studio diagnostic within 1 week  
- [ ] Update plan todos → completed  

---

*Версия: 2026-Q3 · attr-enrichment-product*
