/* QBR deck — навигация и Chart.js-хелперы. Подключается после chart.umd.min.js */
window.QBRDeck = (function () {
  let cur = 0;
  let slides = [];

  function go(n) {
    if (!slides.length) return;
    slides[cur].classList.remove('active');
    cur = (n + slides.length) % slides.length;
    slides[cur].classList.add('active');
    document.querySelectorAll('#dots .dot').forEach(function (d, i) {
      d.classList.toggle('on', i === cur);
    });
  }

  function init() {
    slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
    var dotsEl = document.getElementById('dots');
    var nav = document.getElementById('nav');
    if (!dotsEl || !nav || !slides.length) return;

    dotsEl.innerHTML = '';
    slides.forEach(function (_, i) {
      var d = document.createElement('button');
      d.type = 'button';
      d.className = 'dot' + (i === 0 ? ' on' : '');
      d.setAttribute('aria-label', 'Слайд ' + (i + 1));
      d.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        go(i);
      });
      dotsEl.appendChild(d);
    });

    var prev = document.getElementById('prev');
    var next = document.getElementById('next');
    if (prev) {
      prev.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        go(cur - 1);
      });
    }
    if (next) {
      next.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        go(cur + 1);
      });
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'PageDown' || (e.key === ' ' && e.target.tagName !== 'INPUT')) {
        e.preventDefault();
        go(cur + 1);
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault();
        go(cur - 1);
      } else if (e.key === 'Home') {
        go(0);
      } else if (e.key === 'End') {
        go(slides.length - 1);
      }
    });

    bindReportButtons();
  }

  function runWhenReady(fn) {
    if (document.readyState === 'complete') fn();
    else window.addEventListener('load', fn);
  }

  function destroyChart(elOrId) {
    if (typeof Chart === 'undefined') return;
    var el = typeof elOrId === 'string' ? document.getElementById(elOrId) : elOrId;
    if (!el) return;
    var c = Chart.getChart(el);
    if (c) c.destroy();
  }

  function spark(id, data, color) {
    if (typeof Chart === 'undefined') return;
    destroyChart(id);
    var el = document.getElementById(id);
    if (!el || !data || !data.length) return;
    new Chart(el, {
      type: 'line',
      data: {
        labels: data.map(function (_, i) { return i; }),
        datasets: [{
          data: data,
          borderColor: color,
          backgroundColor: color + '22',
          fill: true,
          tension: 0.35,
          pointRadius: 0,
          borderWidth: 2.5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { display: false }, y: { display: false } }
      }
    });
  }

  function barH(id, labels, values, colors) {
    if (typeof Chart === 'undefined') return;
    destroyChart(id);
    var el = document.getElementById(id);
    if (!el) return;
    new Chart(el, {
      type: 'bar',
      data: { labels: labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 6, barThickness: 28 }] },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { ticks: { callback: function (v) { return v; } } }, y: { grid: { display: false } } }
      }
    });
  }

  function doughnut(id, labels, values, colors) {
    if (typeof Chart === 'undefined') return;
    destroyChart(id);
    var el = document.getElementById(id);
    if (!el) return;
    new Chart(el, {
      type: 'doughnut',
      data: { labels: labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 0 }] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '42%',
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 14, font: { size: 12 } } } }
      }
    });
  }

  function getData() {
    var dataEl = document.getElementById('deck-data');
    if (!dataEl) return {};
    try { return JSON.parse(dataEl.textContent); } catch (e) { return {}; }
  }

  function b64ToUtf8(b64) {
    var binary = atob(b64);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new TextDecoder('utf-8').decode(bytes);
  }

  function downloadReport(key) {
    var rep = (getData().embedded_reports || {})[key];
    if (!rep || !rep.b64) {
      alert('Отчёт недоступен');
      return;
    }
    var html = b64ToUtf8(rep.b64);
    var blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = rep.filename || (key + '.html');
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function bindReportButtons() {
    document.querySelectorAll('.btn-report-dl').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        downloadReport(btn.getAttribute('data-report'));
      });
    });
  }

  /** Стандартные графики product-deck из deck-data */
  function initProductCharts() {
    var DATA = getData();
    var K = DATA.kpi || {};
    var SP = DATA.sparklines || {};

    if (SP.ndcg) QBRDeck.spark('sparkNdcg', SP.ndcg, '#6366f1');
    if (SP.zero) QBRDeck.spark('sparkZero', SP.zero, '#f59e0b');
    if (SP.class_e) QBRDeck.spark('sparkClassE', SP.class_e, '#10b981');

    var zp = document.getElementById('zeroPct');
    if (zp && K.zero_monthly && K.zero_monthly.length) {
      destroyChart('zeroPct');
      new Chart(zp, {
        type: 'line',
        data: {
          labels: K.zero_monthly.map(function (z) { return z.label; }),
          datasets: [{
            label: 'Нулевая выдача %',
            data: K.zero_monthly.map(function (z) { return z.value; }),
            borderColor: '#f59e0b',
            backgroundColor: '#f59e0b22',
            fill: true,
            tension: 0.3,
            borderWidth: 2.5
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { min: 0, ticks: { callback: function (v) { return v + '%'; } } } }
        }
      });
    }

    var serp = DATA.serp_classes;
    if (serp) {
      destroyChart('serpBeforeAfter');
      var sb = document.getElementById('serpBeforeAfter');
      if (sb) {
        new Chart(sb, {
          type: 'bar',
          data: {
            labels: ['Class E', 'Class S', 'Class I', 'Class C'],
            datasets: [
              { label: 'До', data: [serp.before.e, serp.before.s, serp.before.i, serp.before.c], backgroundColor: '#94a3b8', borderRadius: 6 },
              { label: 'После', data: [serp.after.e, serp.after.s, serp.after.i, serp.after.c], backgroundColor: '#6366f1', borderRadius: 6 }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } },
            scales: { y: { ticks: { callback: function (v) { return v + '%'; } } } }
          }
        });
      }
    }

    var lex = DATA.lexicon;
    if (lex) {
      doughnut('lexiconPie', ['Закрыто', 'Остаток gap'], [lex.closed_pct, lex.gap_pct], ['#10b981', '#e2e8f0']);
    }
  }

  return {
    init: init,
    go: go,
    runWhenReady: runWhenReady,
    destroyChart: destroyChart,
    spark: spark,
    barH: barH,
    doughnut: doughnut,
    getData: getData,
    downloadReport: downloadReport,
    bindReportButtons: bindReportButtons,
    initProductCharts: initProductCharts
  };
})();
