# 04. Процесс продаж (фазы 0–9)

## Полный playbook

| Фаза | Название | Срок | Кто | Инструмент | Выход |
|------|----------|------|-----|------------|-------|
| **0** | Квалификация | 15–30 мин | Sales | Чеклист | Go/No-go |
| **1** | Диагностика | 1–3 дня | Analyst + Studio | Wizard steps 1–5 | lexicon_gap JSON |
| **2** | Impact forecast | 1–2 дня | Analyst | Studio step 7 `/api/run` | `*_attribute_impact_data.json` |
| **3** | Рекомендация | 2–4 часа | PM | Decision tree | 1-pager: стрим + атрибуты |
| **4** | КП | 1 день | Sales + PM | pricing_calculator + proposal_builder | `partner-proposal.html` |
| **5** | Согласование | 1–2 недели | Sales | Deck на встрече | Подписанный scope |
| **6** | Batch extraction | 1–4 недели | Eng | image_description / attributes_extraction | CSV results |
| **7** | Dashboard upload | 1–3 дня | Eng + TOTP партнёра | dashboard_feed_attributes | `ok=N failed=0` |
| **8** | Post-impl eval | 2–4 недели после | Analyst | Studio NDCG + quality eval | QBR-style отчёт |
| **9** | Recurring (если есть) | Ongoing | Eng | new_offers_pipeline | Monthly delta |

---

## Фаза 0: Квалификация

**Чеклист Go/No-go:**

- [ ] site_id известен
- [ ] MRR ≥ 30 000 ₽ (иначе — только пилот / отказ)
- [ ] Есть YML/XML фид или URL
- [ ] Доступ к CH / Sort API (или запросим)
- [ ] Вертикаль определена
- [ ] Партнёр согласен на Dashboard custom attrs
- [ ] Есть измеримый lexicon gap (или потенциал после диагностики)

**No-go сигналы:** партнёр хочет переписать PIM; нет фида; MRR < 30k без appetite на пилот.

---

## Фаза 1–2: Диагностика и прогноз

1. Загрузить фид в **Attr Impact Studio** (порт 5050).
2. Пройти Wizard: lexicon gap, current_attrs audit, impact run.
3. Экспортировать `*_attribute_impact_data.json`.
4. Зафиксировать baseline NDCG (если доступен CH).

**SLA:** 3 рабочих дня с момента получения фида.

---

## Фаза 3: Рекомендация (1-pager)

Содержание:

- Рекомендуемый стрим (text / vision / оба)
- Список атрибутов (3–7 приоритетных)
- Прогноз: zero_to_nonzero, product_reach
- Ориентир batch + recurring

---

## Фаза 4: Коммерческое предложение

```powershell
py -3.13 tools/proposal_builder.py ^
  --partner "Ozerki" ^
  --site-id 6390 ^
  --mrr 150000 ^
  --impact-json "path\to\ozerki_attribute_impact_data.json" ^
  --output decks/generated/ozerki-proposal.html
```

+ [pricing_calculator.html](../tools/pricing_calculator.html) для согласования цифр.

**SLA:** 1 день после impact run.

---

## Фаза 6–7: Delivery

| Стрим | Репозиторий | Типичный срок |
|-------|-------------|---------------|
| Vision 50k SKU | image_description | 2–3 недели (GPU) |
| Text 50k SKU | attributes_extraction | 1–2 недели |
| Dashboard upload | dashboard_feed_attributes | 1–3 дня (+ TOTP) |

**Критерий успеха заливки:** `ok=N failed=0`, ключи в `dashboard_sent.json`.

---

## Фаза 8: Post-impl eval

- NDCG@20 до/после (Studio)
- Zero% monthly trend
- Class E/S/I/C (если есть SERP audit)
- QBR-deck для партнёра

**Срок:** 2–4 недели после заливки (стабилизация индекса).

---

## Фаза 9: Recurring

- Мониторинг новинок в фиде
- Еженедельный/ежемесячный delta extraction
- Тариф: 5–10% MRR (см. [05_PRICING.md](05_PRICING.md))

---

## Роли и RACI

| Роль | Фазы | Ответственность |
|------|------|-----------------|
| Sales | 0, 4, 5 | Квалификация, КП, согласование |
| PM | 3, 4 | Стрим, scope, pricing approval |
| Analyst | 1, 2, 8 | Studio, метрики, QBR |
| Eng | 6, 7, 9 | Extraction, upload, recurring |

---

*Версия: 2026-Q3*
