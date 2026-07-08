# 04. Процесс продаж (фазы 0–9)

## Назначение

Повторяемый playbook от первого контакта до recurring и QBR. Каждая фаза имеет **владельца**, **SLA**, **артефакт на выходе** и **критерий готовности** к следующей фазе.

---

## Сводная таблица фаз

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

## Фаза 0: Квалификация (15–30 мин)

**Цель:** не тратить analyst time на нецелевых партнёров.

**Чеклист Go/No-go:**

- [ ] site_id известен
- [ ] MRR ≥ 30 000 ₽ (иначе — только пилот / отказ)
- [ ] Есть YML/XML фид или URL
- [ ] Доступ к CH / Sort API (или запросим у партнёра)
- [ ] Вертикаль определена
- [ ] Партнёр согласен на Dashboard custom attrs
- [ ] Есть измеримый lexicon gap (или потенциал после диагностики)
- [ ] Нет блокера «переписать PIM вместо Dashboard»

**No-go сигналы:**

- Партнёр хочет только PIM enrichment без search
- Нет фида и не будет в горизонте 2 недель
- MRR < 30k без budget на пилот
- Отказ от любых custom attributes в Dashboard

**Артефакт:** запись в CRM + тег `attr-enrichment-qualified` / `no-go`.

---

## Фаза 1–2: Диагностика и прогноз (3–5 раб. дней)

### Фаза 1 — Диагностика

1. Получить фид (URL или файл) — зафиксировать дату снимка
2. Загрузить в **Attr Impact Studio** (порт 5050)
3. Wizard steps 1–5: feed parse, lexicon gap, current_attrs sample
4. Экспорт: lexicon gap report, список candidate attributes

### Фаза 2 — Impact forecast

1. Studio step 7: `/api/run` impact simulation
2. Экспорт: `{partner}_attribute_impact_data.json`
3. Зафиксировать baseline NDCG (если CH доступен)
4. Заполнить поля: `zero_to_nonzero_freq`, `product_reach_rows`, `lexicon_gap_closure_pct`

**SLA:** 3 рабочих дня с момента получения фида.

**Escalation:** если фид > 500k SKU — согласовать sampling scope с PM.

---

## Фаза 3: Рекомендация (1-pager)

**Владелец:** PM (2–4 часа после impact JSON).

**Содержание 1-pager:**

| Секция | Содержание |
|--------|------------|
| Executive summary | 3 предложения: боль → стрим → прогноз |
| Recommended stream | text / vision / both + decision tree обоснование |
| Attribute list | 3–7 приоритетных атрибутов с примерами значений |
| Forecast | zero_to_nonzero, product_reach, gap closure % |
| Pricing orientir | batch + recurring из калькулятора |
| Risks | фото quality, current_attrs noise, TOTP |
| Next step | встреча с deck + scope sign-off |

**Шаблон:** можно собрать из Studio export + [03_SEGMENTS](03_SEGMENTS_AND_USE_CASES.md).

---

## Фаза 4: Коммерческое предложение (1 день)

**SLA:** 1 рабочий день после impact run.

```powershell
py -3.13 tools/proposal_builder.py ^
  --partner "Ozerki" ^
  --site-id 6390 ^
  --mrr 150000 ^
  --vertical "Аптека" ^
  --new-per-week 400 ^
  --impact-json "path\to\ozerki_attribute_impact_data.json" ^
  --output decks/generated/ozerki-proposal.html
```

**Пакет для sales:**

- [ ] `partner-proposal.html` (персональный deck)
- [ ] Скрин pricing_calculator с согласованными цифрами
- [ ] 1-pager (фаза 3)
- [ ] 2–3 релевантных кейса из portfolio

---

## Фаза 5: Согласование (1–2 недели)

**Активности:**

- Презентация [client-overview.html](../decks/client-overview.html) или partner proposal
- Согласование scope: SKU count, attribute list, QA policy
- Юридическое: доп. соглашение к search contract
- IT: подтверждение Dashboard custom attrs + контакт для TOTP

**Критерий выхода:** подписанный scope (email или допник) с batch price, optional recurring, timeline.

---

## Фаза 6–7: Delivery

| Стрим | Репозиторий | Типичный срок | QA |
|-------|-------------|---------------|-----|
| Vision 50k SKU | image_description | 2–3 недели (GPU) | 1% manual sample |
| Text 50k SKU | attributes_extraction | 1–2 недели | collision check vs feed |
| Dashboard upload | dashboard_feed_attributes | 1–3 дня (+ TOTP) | `ok=N failed=0` |

**Фаза 7 — заливка:**

1. Eng готовит CSV `(external_id, attribute_name, attribute_value)`
2. Открыть UI TOTP: `scripts/befree_dashboard_upload_ui.py` (порт 8766) или Gradio dash push
3. Партнёр вводит свежий TOTP
4. Проверка: `failed=0`, обновить `dashboard_sent.json`

**Критерий успеха заливки:** `ok=N failed=0`, ключи в `dashboard_sent.json`, нет дублей.

---

## Фаза 8: Post-impl eval (2–4 недели после заливки)

**Чеклист analyst:**

- [ ] NDCG@20 до/после (Studio `ndcg_store`)
- [ ] Zero% monthly trend (CH / Studio zeros)
- [ ] Class E/S/I/C (если SERP audit доступен)
- [ ] Rank-list: топ zero→result запросов
- [ ] QBR deck для партнёра (Petrovich style)

**SLA:** отчёт через 4 недели после `failed=0` upload.

---

## Фаза 9: Recurring (ongoing)

- Мониторинг новинок в фиде (weekly delta)
- Extraction pipeline на new offers only
- Monthly upload + tracking в `dashboard_sent.json`
- Тариф: 5–10% MRR ([05_PRICING.md](05_PRICING.md))
- Quarterly mini-QBR с zero trend

---

## Роли и RACI

| Роль | R | A | C | I | Фазы |
|------|---|---|---|---|------|
| Sales | Квалификация, КП, согласование | A | PM, Analyst | Eng | 0, 4, 5 |
| PM | Стрим, scope, pricing approval | A | Sales, Eng | Analyst | 3, 4, 5 |
| Analyst | Studio, метрики, QBR | R | PM | Sales | 1, 2, 8 |
| Eng | Extraction, upload, recurring | R | PM | Analyst | 6, 7, 9 |

---

## Внутренние SLA (summary)

| Этап | SLA |
|------|-----|
| Диагностика + impact | 3 раб. дня от фида |
| КП после impact | 1 раб. день |
| Batch 50k vision | 2–3 недели |
| Batch 50k text | 1–2 недели |
| Post-impl report | 4 недели после upload |

---

## Эскалации

| Ситуация | Кому | Действие |
|----------|------|----------|
| Impact слабый (< 5% gap) | PM | Пересмотр scope или no-go |
| GPU queue > 2 нед ожидания | Eng lead | Приоритизация / scaling |
| TOTP недоступен > 5 дней | Sales → партнёр | Pause фазы 7, не начинать batch |
| failed > 0 на upload | Eng | Rollback keys, fix CSV |

---

*Версия: 2026-Q3 · attr-enrichment-product*
