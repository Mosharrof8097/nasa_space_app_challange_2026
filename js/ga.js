/* Section 5 — GA convergence */
(function () {
  'use strict';
  const ES = window.ES;
  const DASH = [[], [8, 4], [2, 3], [10, 3, 2, 3]];
  const STYLE = ['circle', 'rect', 'triangle', 'rectRot'];

  ES.renderGA = function (d) {
    ES.chartDefaults();
    const bs = (d.biomes || []).filter((b) => Array.isArray(b.ga_convergence) && b.ga_convergence.length);
    const cv = document.getElementById('ga-chart');
    if (!bs.length) { cv.parentNode.innerHTML = '<p class="caption">GA convergence history pending.</p>'; return; }
    const maxGen = Math.max.apply(null, bs.map((b) => Math.max.apply(null, b.ga_convergence.map((g) => g.generation))));
    const labels = []; for (let i = 1; i <= maxGen; i++) labels.push(i);
    const series = (b, key) => labels.map((g) => { const r = b.ga_convergence.find((x) => x.generation === g); return r && ES.isNum(r[key]) ? r[key] : null; });
    const best = bs.map((b, i) => ({
      label: b.name + ' — best', data: series(b, 'best_fitness'), borderColor: ES.biomeColor(b.class_id), backgroundColor: ES.biomeColor(b.class_id),
      borderWidth: 2.5, borderDash: DASH[i % 4], pointStyle: STYLE[i % 4], pointRadius: 3, pointHoverRadius: 6, tension: 0.25, spanGaps: true,
    }));
    const avg = bs.map((b) => ({
      label: b.name + ' — average', data: series(b, 'avg_fitness'), borderColor: ES.biomeColor(b.class_id) + '88', borderWidth: 1.2, borderDash: [2, 4], pointRadius: 0, tension: 0.25, hidden: true, spanGaps: true,
    }));
    const chart = new Chart(cv.getContext('2d'), {
      type: 'line', data: { labels, datasets: best.concat(avg) },
      options: {
        responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        animation: ES.reduced ? false : { duration: 1400, easing: 'easeOutQuart' },
        scales: { x: { title: { display: true, text: 'Generation' }, grid: { display: false }, ticks: { maxTicksLimit: 15 } }, y: { title: { display: true, text: 'Fitness (higher is better)' } } },
        plugins: { legend: { labels: { usePointStyle: true, boxWidth: 8, filter: (it, data) => it.datasetIndex < best.length } } },
      },
    });
    document.getElementById('ga-avg').addEventListener('change', (e) => {
      avg.forEach((_, i) => { chart.data.datasets[best.length + i].hidden = !e.target.checked; });
      chart.update();
    });
  };
})();
