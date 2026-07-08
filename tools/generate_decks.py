#!/usr/bin/env python3
"""Generate internal-defense.html and client-overview.html decks."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "decks/data/product-default.json").read_text(encoding="utf-8"))
DECK_DATA = json.dumps(DATA, ensure_ascii=False)

HEAD = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1280">
<title>{title}</title>
<link rel="stylesheet" href="engine/qbr-deck.css">
</head>
<body>
<div class="deck" id="deck">
"""

FOOT = """
</div>
<nav class="nav-dots" id="nav" aria-label="Навигация">
  <button type="button" id="prev" aria-label="Предыдущий">‹</button>
  <div id="dots"></div>
  <button type="button" id="next" aria-label="Следующий">›</button>
</nav>
<script type="application/json" id="deck-data">{deck_data}</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="engine/qbr-deck.js"></script>
<script>
QBRDeck.init();
QBRDeck.runWhenReady(function () {{ QBRDeck.initProductCharts(); }});
</script>
</body>
</html>
"""


def slide(num: int, tag: str, extra_class: str, body: str, active: bool = False) -> str:
    cls = f"slide {extra_class} active" if active else f"slide {extra_class}"
    return f'<section class="{cls.strip()}">\n<span class="slide-num">{num}</span>\n<div class="slide-head"><span class="tag">{tag}</span></div>\n<div class="slide-body">\n{body}\n</div>\n</section>\n'


def title_cover(num: int, title: str, sub: str, period: str, active: bool = False) -> str:
    cls = "slide title-cover active" if active else "slide title-cover"
    return f"""<section class="{cls}">
<span class="slide-num">{num}</span>
<div class="title-wrap">
  <div class="title-frame">
    <div class="title-bg title-bg-gradient"></div>
    <div class="title-overlay">
      <h1>{title}</h1>
      <p class="sub">{sub}</p>
      <p class="period">{period}</p>
    </div>
    <span class="slide-num-in">{num}</span>
  </div>
</div>
</section>
"""


def build_internal_defense() -> str:
    slides = []
    n = 1
    slides.append(title_cover(n, "Обогащение каталога<br>для поиска", "Единый B2B-продукт Diginetica", "Защита продукта · 2026-Q3", active=True))
    n += 1

    slides.append(slide(n, "Проблема", "", """
<h2>Три боли enterprise-каталога</h2>
<ul class="big-list glass fill-card" style="padding:28px 32px">
  <li><strong>Нули в поиске</strong>Покупатель ищет «кольцо змея», «стельки» — в фиде нет полей → zero или чай вместо стелек.</li>
  <li><strong>IT-очередь 6–18 месяцев</strong>30–50k SKU: новый атрибут в YML = согласования, PIM, интеграции.</li>
  <li><strong>Визуал не в индексе</strong>Цвет, узор, OCR с упаковки — на фото есть, в фиде нет или противоречит тексту.</li>
</ul>
"""))
    n += 1

    slides.append(slide(n, "Решение", "", """
<h2>Два стрима + оценка до работ</h2>
<div class="grid2">
  <div class="glass fill-card">
    <h3 class="card-h3">📝 Текстовый стрим</h3>
    <p class="biz-p">attributes_extraction — извлечение из описаний и params. Grocery 130 attrs, Kids 8858.</p>
    <p class="foot-note">Порт 8501 · SpaCy / LLM</p>
  </div>
  <div class="glass fill-card">
    <h3 class="card-h3">👁 Vision-стрим</h3>
    <p class="biz-p">image_description — OCR, принт, форма ювелирки, цвет металла. Befree, аптека, дискаунт.</p>
    <p class="foot-note">Порт 7860 · Ollama vision</p>
  </div>
</div>
<div class="glass" style="margin-top:14px">
  <strong style="color:var(--accent)">Attr Impact Studio :5050</strong> — диагностика lexicon gap, прогноз ROI, NDCG до/после
</div>
"""))
    n += 1

    slides.append(slide(n, "Ценность", "", """
<h2>Измеримые outcomes для партнёра</h2>
<div class="grid4">
  <div class="glass goal-card"><div class="goal-label">Нулевая выдача</div><div class="goal-metric">−33%</div><div class="goal-note">Ювелирка: запросы form=snake, skull</div><div class="goal-art"><span style="font-size:48px">📉</span></div></div>
  <div class="glass goal-card"><div class="goal-label">NDCG@20</div><div class="goal-metric">+9%</div><div class="goal-note">Средний uplift vision-кейсов</div><div class="goal-art"><span style="font-size:48px">📈</span></div></div>
  <div class="glass goal-card"><div class="goal-label">Class E</div><div class="goal-metric">+2.6pp</div><div class="goal-note">Аптека: точная выдача в SERP</div><div class="goal-art"><span style="font-size:48px">✓</span></div></div>
  <div class="glass goal-card"><div class="goal-label">Новая лексика</div><div class="goal-metric">49%</div><div class="goal-note">Befree: truly_new в индексе</div><div class="goal-art"><span style="font-size:48px">✨</span></div></div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Процесс", "", """
<h2>Замкнутый цикл без PIM</h2>
<div class="flow-diagram glass fill-card" style="padding:32px">
  <div class="flow-step"><strong>1. Studio</strong><br>Диагностика<br>Impact run</div>
  <span class="flow-arrow">→</span>
  <div class="flow-step"><strong>2. Extract</strong><br>Text / Vision<br>CSV</div>
  <span class="flow-arrow">→</span>
  <div class="flow-step"><strong>3. Dashboard</strong><br>Custom attrs<br>TOTP upload</div>
  <span class="flow-arrow">→</span>
  <div class="flow-step"><strong>4. QBR</strong><br>NDCG / zero<br>Отчёт</div>
</div>
<p class="foot-note">Партнёр не меняет мастер-фид — только поисковые custom attributes</p>
"""))
    n += 1

    slides.append(slide(n, "Метрики", "slide-kpi", """
<h2>Портфолио: до и после</h2>
<div class="grid3 grid3-kpi">
  <div class="glass metric-card"><div class="lbl">NDCG@20 Δ</div><div class="value" style="color:var(--accent)">+0.003</div><div class="sparkline"><canvas id="sparkNdcg"></canvas></div></div>
  <div class="glass metric-card"><div class="lbl">Zero %</div><div class="value" style="color:#f59e0b">−33%</div><div class="sparkline"><canvas id="sparkZero"></canvas></div></div>
  <div class="glass metric-card"><div class="lbl">Class E</div><div class="value" style="color:var(--accent2)">+2.6pp</div><div class="sparkline"><canvas id="sparkClassE"></canvas></div></div>
</div>
<div class="insight-row insight-row-kpi">
  <div class="insight green"><strong>Вывод</strong>Даже малый ndcg на большом baseline = тысячи лучших сессий</div>
  <div class="insight"><strong>Вывод</strong>Class I −2.2pp — сильнее для UX, чем средний ndcg</div>
</div>
<div class="chart-box compact"><canvas id="zeroPct"></canvas></div>
"""))
    n += 1

    slides.append(slide(n, "Кейс", "slide-patterns-ai", """
<h2>Ювелирка · Vision</h2>
<div class="grid2 pattern-stats">
  <div class="glass metric-card"><div class="lbl">Zero reduction</div><div class="value">−33%</div></div>
  <div class="glass metric-card"><div class="lbl">NDCG@20</div><div class="value">+9%</div></div>
</div>
<div class="pattern-examples">
  <div class="glass pattern-ex"><div style="font-size:64px;padding:20px">🐍</div><div class="pat-label">form=snake</div><div class="pat-sub">«кольцо змея» — 842 запр./мес</div></div>
  <div class="glass pattern-ex"><div style="font-size:64px;padding:20px">💀</div><div class="pat-label">form=skull</div><div class="pat-sub">«кольцо череп» — 615 запр./мес</div></div>
</div>
<div class="insight-row pattern-insights">
  <div class="insight green"><strong>Бизнес</strong>Запросы без результата закрыты без изменения PIM</div>
  <div class="insight"><strong>Атрибуты</strong>form, metal_color → Dashboard</div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Кейс", "slide-kpi", """
<h2>Аптека · OCR упаковки</h2>
<div class="chart-box tall"><canvas id="serpBeforeAfter"></canvas></div>
<div class="insight-row">
  <div class="insight green"><strong>Story</strong>«Стельки» → чай для сосудов. После OCR — корректный товар</div>
  <div class="insight"><strong>Метрики</strong>Precision +0.010 · Class E +2.6pp · Class I −2.2pp</div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Кейс", "slide-patterns-ai", """
<h2>Befree · Fashion OCR + принт</h2>
<div class="grid2 pattern-stats">
  <div class="glass metric-card"><div class="lbl">Dashboard rows</div><div class="value">1 747</div></div>
  <div class="glass metric-card"><div class="lbl">Truly new lexicon</div><div class="value">49%</div></div>
</div>
<div class="pattern-examples">
  <div class="glass pattern-ex"><div style="font-size:48px;padding:16px">👕 OCR</div><div class="pat-label">digi_attr_image</div><div class="pat-sub">Надписи на принте</div></div>
  <div class="glass pattern-ex"><div style="font-size:48px;padding:16px">🐆 Pattern</div><div class="pat-label">digi_attr_pattern</div><div class="pat-sub">Леопард, полоска, графика</div></div>
</div>
<div class="chart-box compact"><canvas id="lexiconPie"></canvas></div>
"""))
    n += 1

    slides.append(slide(n, "Кейс", "", """
<h2>Текстовый стрим</h2>
<div class="grid2">
  <div class="glass fill-card metric-card">
    <div class="lbl">Детский мир (8858)</div>
    <div class="value">95+ attrs</div>
    <p class="goal-note">LoRA + vocabulary gaps: возраст, персонажи, материалы</p>
  </div>
  <div class="glass fill-card metric-card">
    <div class="lbl">Grocery (221)</div>
    <div class="value">130 attrs</div>
    <p class="goal-note">Массовое извлечение из supplier-описаний</p>
  </div>
</div>
<div class="glass" style="margin-top:14px">
  <div class="lbl">Дискаунт · Vision OCR</div>
  <div class="value" style="font-size:32px">11 000 SKU</div>
  <p class="goal-note">Zero→result по брендам и составу с упаковки</p>
</div>
"""))
    n += 1

    slides.append(slide(n, "Studio", "", """
<h2>Attr Impact Studio — 7 шагов Wizard</h2>
<div class="research-grid">
  <div class="glass research-tile"><div class="research-icon">1</div><div><h4>Фид</h4><p>Загрузка YML/XML, site_id</p></div></div>
  <div class="glass research-tile"><div class="research-icon">2</div><div><h4>Current attrs</h4><p>Аудит шума (кейс Petrovich)</p></div></div>
  <div class="glass research-tile"><div class="research-icon">3</div><div><h4>Lexicon gap</h4><p>Запросы без покрытия в фиде</p></div></div>
  <div class="glass research-tile"><div class="research-icon">4</div><div><h4>План CSV</h4><p>Какие атрибуты заливать</p></div></div>
  <div class="glass research-tile"><div class="research-icon">5</div><div><h4>NDCG baseline</h4><p>До внедрения</p></div></div>
  <div class="glass research-tile"><div class="research-icon">6</div><div><h4>Impact run</h4><p>zero_to_nonzero, product_reach</p></div></div>
  <div class="glass research-tile"><div class="research-icon">7</div><div><h4>Отчёт</h4><p>JSON → proposal_builder</p></div></div>
  <div class="glass research-tile"><div class="research-icon">→</div><div><h4>Диагностика бесплатно</h4><p>Для new partners — entry в воронку</p></div></div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Архитектура", "", """
<h2>Три репозитория — один продукт</h2>
<div class="grid3">
  <div class="glass fill-card"><h3 class="card-h3">attr-impact-studio</h3><p>:5050 · Flask<br>Оценка, NDCG, decks data</p></div>
  <div class="glass fill-card"><h3 class="card-h3">attributes_extraction</h3><p>:8501 · Streamlit<br>Text stream</p></div>
  <div class="glass fill-card"><h3 class="card-h3">image_description</h3><p>:7860 · Gradio<br>Vision stream</p></div>
</div>
<p class="foot-note">attr-enrichment-product — product hub (docs, decks, pricing). Код трёх репо не дублируем.</p>
"""))
    n += 1

    slides.append(slide(n, "Enterprise", "slide-attrs", """
<h2>Почему партнёр не делает сам</h2>
<div class="grid2">
  <div class="glass fill-card">
    <h3 class="card-h3">Путь PIM (6–18 мес)</h3>
    <ul class="rank-list">
      <li><span class="q">Согласование полей</span><span class="v">3 мес</span></li>
      <li><span class="q">Разметка 50k SKU</span><span class="v">6+ мес</span></li>
      <li><span class="q">Выкатка в поиск</span><span class="v">+ интеграция</span></li>
    </ul>
  </div>
  <div class="glass fill-card">
    <h3 class="card-h3">Наш путь (2–4 нед)</h3>
    <p class="biz-p accent">Studio → CSV → Dashboard API</p>
    <p class="biz-p">Кейс Petrovich: 42% шумных current_attrs — сначала audit, потом enrichment</p>
    <div class="attr-danger-tags">
      <span class="attr-danger-tag">дубликаты</span>
      <span class="attr-danger-tag">конфликт значений</span>
      <span class="attr-danger-tag">шум в ранжировании</span>
    </div>
  </div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Pricing", "", """
<h2>Ценообразование</h2>
<div class="grid3 pricing-highlight">
  <div class="glass goal-card"><div class="goal-label">Batch (разовый)</div><div class="goal-metric">1×MRR</div><div class="goal-note">Весь согласованный срез каталога</div></div>
  <div class="glass goal-card"><div class="goal-label">Recurring</div><div class="goal-metric">5–10%</div><div class="goal-note">По потоку новинок в неделю</div></div>
  <div class="glass goal-card"><div class="goal-label">Минимум</div><div class="goal-metric">30k ₽</div><div class="goal-note">При MRR = 30 000 ₽</div></div>
</div>
<div class="glass" style="margin-top:14px">
  <p>≤500 нов./нед → 5% · 501–2000 → 7.5% · &gt;2000 → 10%</p>
  <p class="foot-note">Калькулятор: tools/pricing_calculator.html</p>
</div>
"""))
    n += 1

    slides.append(slide(n, "Процесс", "", """
<h2>Фазы 0–9</h2>
<div class="work-grid">
  <div class="glass work-block"><h3>Продажи</h3><ul>
    <li>0 Квалификация · 1–2 Диагностика Studio</li>
    <li>4 КП · 5 Согласование</li>
  </ul></div>
  <div class="glass work-block"><h3>Delivery</h3><ul>
    <li>6 Batch extraction · 7 Dashboard upload</li>
    <li>8 Post-impl eval · 9 Recurring</li>
  </ul></div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Сегменты", "", """
<h2>Кому продаём</h2>
<div class="grid3">
  <div class="glass fill-card"><h3 class="card-h3">Enterprise</h3><p>MRR 500k–3M+<br>Batch + recurring<br>Befree, Ozerki</p></div>
  <div class="glass fill-card"><h3 class="card-h3">Mid-market</h3><p>MRR 100–500k<br>Text чаще<br>Zolla, Parfum Lider</p></div>
  <div class="glass fill-card"><h3 class="card-h3">New partner</h3><p>Диагностика бесплатно<br>Пилот batch<br>Demo deck с их цифрами</p></div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Риски", "", """
<h2>Честные ограничения</h2>
<ul class="big-list glass fill-card" style="padding:24px 28px">
  <li><strong>Прогноз ≠ CTR</strong>Нужен пилот и NDCG до/после — не обещаем точную выручку без данных.</li>
  <li><strong>Качество фото</strong>Vision зависит от картинок в фиде; Phase1 отсекает мусор.</li>
  <li><strong>TOTP friction</strong>Заливка требует код партнёра — UI на :8766.</li>
  <li><strong>Три UI</strong>Решаем product hub, не рефакторим ядро на этапе 1.</li>
</ul>
"""))
    n += 1

    slides.append(f"""<section class="slide slide-dark slide-plan">
<span class="slide-num">{n}</span>
<div class="slide-head"><span class="tag">План</span></div>
<h2>Ask · Next steps</h2>
<div class="plan-grid proposals">
  <div class="plan-tile"><div class="plan-icon">✓</div><p>Утвердить pricing: 1×MRR batch, 5–10% recurring</p></div>
  <div class="plan-tile"><div class="plan-icon">👤</div><p>Выделить analyst на Studio-диагностику (0.25 FTE)</p></div>
  <div class="plan-tile"><div class="plan-icon">🎯</div><p>Пилот 0.2×MRR для new partners — опционально</p></div>
  <div class="plan-tile"><div class="plan-icon">📊</div><p>Первые 3 КП: Ozerki, Befree, mid-market grocery</p></div>
</div>
<p class="plan-foot">attr-enrichment-product · product/09_INTERNAL_DEFENSE.md</p>
</section>
""")

    return HEAD.format(title="Обогащение каталога — защита") + "".join(slides) + FOOT.format(deck_data=DECK_DATA)


def build_client_overview() -> str:
    """14 slides for clients."""
    slides = []
    n = 1
    slides.append(title_cover(n, "Обогащение каталога", "Больше находок в поиске — без изменения вашего PIM", "Diginetica · для партнёров search", active=True))
    n += 1

    # Reuse key slides from internal (simplified)
    slides.append(slide(n, "Проблема", "", """
<h2>Ваш покупатель ищет то, чего нет в карточке</h2>
<ul class="big-list glass fill-card" style="padding:24px 28px">
  <li><strong>Нулевая выдача</strong>Популярные запросы без результата — потерянные продажи.</li>
  <li><strong>Неточная выдача</strong>Fallback вместо точного товара (нерелевантные позиции в топе).</li>
  <li><strong>Фото ≠ фид</strong>Цвет, принт, надпись на упаковке не попадают в поиск.</li>
</ul>
"""))
    n += 1

    slides.append(slide(n, "Решение", "", """
<h2>Мы добавляем атрибуты в поиск — не в ваш PIM</h2>
<div class="grid2">
  <div class="glass fill-card"><h3 class="card-h3">Из текста</h3><p>Материал, состав, возраст — из описаний поставщиков</p></div>
  <div class="glass fill-card"><h3 class="card-h3">С фото</h3><p>OCR, принт, форма, цвет — с карточек товаров</p></div>
</div>
<div class="glass" style="margin-top:14px;text-align:center"><strong>Заливка через Diginetica Dashboard</strong> — без очереди в ваш IT</div>
"""))
    n += 1

    slides.append(slide(n, "Результат", "", """
<h2>Что вы получаете</h2>
<div class="grid4">
  <div class="glass goal-card"><div class="goal-label">Меньше нулей</div><div class="goal-metric">−33%</div><div class="goal-note">Кейс ювелирка</div><div class="goal-art">📉</div></div>
  <div class="glass goal-card"><div class="goal-label">Лучший топ-20</div><div class="goal-metric">+9%</div><div class="goal-note">NDCG@20</div><div class="goal-art">📈</div></div>
  <div class="glass goal-card"><div class="goal-label">Точнее выдача</div><div class="goal-metric">+2.6pp</div><div class="goal-note">Class E · аптека</div><div class="goal-art">✓</div></div>
  <div class="glass goal-card"><div class="goal-label">Новые слова</div><div class="goal-metric">49%</div><div class="goal-note">SKU с новой лексикой</div><div class="goal-art">✨</div></div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Метрики", "slide-kpi", """
<h2>Доказанный uplift</h2>
<div class="grid3 grid3-kpi">
  <div class="glass metric-card"><div class="lbl">NDCG@20</div><div class="value">+0.003 … +9%</div><div class="sparkline"><canvas id="sparkNdcg"></canvas></div></div>
  <div class="glass metric-card"><div class="lbl">Zero queries</div><div class="value">до −33%</div><div class="sparkline"><canvas id="sparkZero"></canvas></div></div>
  <div class="glass metric-card"><div class="lbl">Precision@20</div><div class="value">+0.010</div><div class="sparkline"><canvas id="sparkClassE"></canvas></div></div>
</div>
<ul class="rank-list glass" style="padding:12px 16px;margin-top:10px">
  <li><span class="n">1</span><span class="q">кольцо змея</span><span class="v">842/мес</span></li>
  <li><span class="n">2</span><span class="q">стельки ортопедические</span><span class="v">1203/мес</span></li>
</ul>
"""))
    n += 1

    # Cases 6-8
    slides.append(slide(n, "Кейс", "slide-patterns-ai", """
<h2>Ювелирный ритейл</h2>
<div class="pattern-examples">
  <div class="glass pattern-ex"><div style="font-size:56px">🐍</div><div class="pat-label">Форма «змея»</div><div class="pat-sub">Zero −33%</div></div>
  <div class="glass pattern-ex"><div style="font-size:56px">💍</div><div class="pat-label">Цвет металла</div><div class="pat-sub">NDCG +9%</div></div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Кейс", "slide-kpi", """
<h2>Аптечная сеть</h2>
<div class="chart-box tall"><canvas id="serpBeforeAfter"></canvas></div>
<div class="insight green glass" style="padding:14px"><strong>Пример</strong> Запрос «стельки» — корректный товар после OCR с упаковки</div>
"""))
    n += 1

    slides.append(slide(n, "Кейс", "", """
<h2>Fashion · OCR и принт</h2>
<div class="grid2">
  <div class="glass metric-card"><div class="lbl">Залито в поиск</div><div class="value">1 747</div></div>
  <div class="glass metric-card"><div class="lbl">Новая лексика</div><div class="value">49%</div></div>
</div>
<div class="chart-box compact"><canvas id="lexiconPie"></canvas></div>
"""))
    n += 1

    slides.append(slide(n, "Диагностика", "", """
<h2>Бесплатная оценка до старта</h2>
<div class="research-grid">
  <div class="glass research-tile"><div class="research-icon">📊</div><div><h4>Lexicon gap</h4><p>Какие запросы не покрыты фидом</p></div></div>
  <div class="glass research-tile"><div class="research-icon">🎯</div><div><h4>Impact forecast</h4><p>Сколько SKU и запросов выиграют</p></div></div>
  <div class="glass research-tile"><div class="research-icon">📈</div><div><h4>NDCG baseline</h4><p>Точка отсчёта до внедрения</p></div></div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Процесс", "", """
<h2>Как это работает для вас</h2>
<div class="flow-diagram glass fill-card" style="padding:24px">
  <div class="flow-step"><strong>Диагностика</strong><br>2–3 дня</div>
  <span class="flow-arrow">→</span>
  <div class="flow-step"><strong>Пилот / batch</strong><br>2–4 нед</div>
  <span class="flow-arrow">→</span>
  <div class="flow-step"><strong>Заливка</strong><br>Dashboard</div>
  <span class="flow-arrow">→</span>
  <div class="flow-step"><strong>Отчёт</strong><br>QBR метрики</div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Цена", "", """
<h2>Прозрачное ценообразование</h2>
<div class="grid2">
  <div class="glass goal-card"><div class="goal-label">Разовый batch</div><div class="goal-metric">1×MRR</div><div class="goal-note">Обработка согласованного каталога</div></div>
  <div class="glass goal-card"><div class="goal-label">Поддержка новинок</div><div class="goal-metric">5–10%</div><div class="goal-note">MRR в месяц по потоку SKU</div></div>
</div>
"""))
    n += 1

    slides.append(slide(n, "Пилот", "", """
<h2>Следующий шаг</h2>
<div class="glass fill-card" style="padding:28px">
  <ul class="big-list">
    <li><strong>Диагностика</strong> — бесплатно, 3 рабочих дня после фида</li>
    <li><strong>Пилот</strong> — 5–10k SKU, метрики до/после</li>
    <li><strong>Масштаб</strong> — полный batch после согласования uplift</li>
  </ul>
</div>
"""))
    n += 1

    slides.append(slide(n, "Контакты", "", """
<h2>Готовы показать цифры на вашем каталоге</h2>
<div class="glass fill-card" style="padding:32px;text-align:center">
  <p style="font-size:22px;font-weight:600;color:var(--accent)">Запросите диагностику lexicon gap</p>
  <p style="margin-top:16px;color:var(--muted)">Diginetica Search · Обогащение каталога</p>
</div>
"""))
    n += 1

    slides.append(f"""<section class="slide title-cover">
<span class="slide-num">{n}</span>
<div class="title-wrap">
  <div class="title-frame">
    <div class="title-bg title-bg-gradient"></div>
    <div class="title-overlay">
      <h1>Спасибо</h1>
      <p class="sub">Диагностика бесплатно</p>
      <p class="period">product@diginetica · Attr Impact Studio</p>
    </div>
  </div>
</div>
</section>
""")

    return HEAD.format(title="Обогащение каталога — обзор") + "".join(slides) + FOOT.format(deck_data=DECK_DATA)


def main() -> None:
    (ROOT / "decks/internal-defense.html").write_text(build_internal_defense(), encoding="utf-8")
    (ROOT / "decks/client-overview.html").write_text(build_client_overview(), encoding="utf-8")
    print("Generated internal-defense.html and client-overview.html")


if __name__ == "__main__":
    main()
