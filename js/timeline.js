/* Section 1 — raw vs harmonized exhibit */
(function () {
  'use strict';
  const ES = window.ES;

  ES.chartDefaults = function () {
    if (!window.Chart) throw new Error('Chart.js not loaded (CDN unreachable?)');
    Chart.defaults.color = '#a3abbd';
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.borderColor = 'rgba(255,255,255,.06)';
  };

  const RAW = [255, 107, 53], HARM = [54, 214, 238];
  const mix = (t, a = 1) => `rgba(${RAW.map((v, i) => Math.round(ES.lerp(v, HARM[i], t))).join(',')},${a})`;

  function indexed(vals, labels) {
    const pre = [];
    vals.forEach((v, i) => { if (ES.isNum(v) && parseInt(labels[i], 10) < 2012) pre.push(v); });
    let base = pre.length ? pre.reduce((a, b) => a + b, 0) / pre.length : null;
    if (!base) { const f = vals.find(ES.isNum); base = f || null; }
    if (!base) return vals.map(() => null);
    return vals.map((v) => (ES.isNum(v) ? (v / base) * 100 : null));
  }

  ES.renderTimeline = function (d) {
    ES.chartDefaults();
    const r = d.raw_vs_harmonized;
    const box = document.getElementById('exhibit');
    if (!r || !Array.isArray(r.labels) || !r.labels.length || !Array.isArray(r.raw) || !Array.isArray(r.harmonized)) {
      box.querySelector('.chart-box').innerHTML = '<p class="caption">Long-range timeline pending: not present in the dataset.</p>';
      return;
    }
    const modeled = r.is_modeled !== false; // default to the honest label if missing
    const cap = document.getElementById('timeline-caption');
    if (!modeled) {
      cap.innerHTML = '<span class="chip chip-warn" style="background:var(--cyan);color:#001418">Measured series</span> Computed from the ingested archive.';
      cap.classList.remove('modeled');
    }
    const labels = r.labels.map(String);
    const rawI = indexed(r.raw, labels), harmI = indexed(r.harmonized, labels);
    const all = rawI.concat(harmI).filter(ES.isNum);
    const ymax = Math.ceil((Math.max.apply(null, all) * 1.1) / 50) * 50;
    const i11 = labels.indexOf('2011'), i12 = labels.indexOf('2012');
    const jump = (arr) => (i11 >= 0 && i12 >= 0 && ES.isNum(arr[i11]) && ES.isNum(arr[i12]) && arr[i11] !== 0 ? (arr[i12] / arr[i11] - 1) * 100 : null);
    const jRaw = jump(r.raw), jHarm = jump(r.harmonized);

    const ctx = document.getElementById('timeline-chart').getContext('2d');
    let t = 0;
    const blend = () => labels.map((_, i) => (ES.isNum(rawI[i]) && ES.isNum(harmI[i]) ? ES.lerp(rawI[i], harmI[i], t) : null));

    const marker = {
      id: 'viirs',
      afterDatasetsDraw(c) {
        if (i12 < 0) return;
        const x = c.scales.x.getPixelForValue(i12), a = c.chartArea, g = c.ctx;
        g.save(); g.setLineDash([5, 5]); g.strokeStyle = 'rgba(255,255,255,.35)'; g.lineWidth = 1;
        g.beginPath(); g.moveTo(x, a.top); g.lineTo(x, a.bottom); g.stroke(); g.setLineDash([]);
        g.fillStyle = '#eef0f5'; g.font = '600 12px ' + Chart.defaults.font.family;
        const txt = '2012: VIIRS joins the record';
        const w = g.measureText(txt).width;
        const left = x - w - 10 > a.left;
        g.textAlign = left ? 'right' : 'left';
        g.fillText(txt, left ? x - 8 : x + 8, a.top + 14);
        g.restore();
      },
    };

    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Raw (ghost)', data: rawI, borderColor: mix(0, 0), borderDash: [6, 5], borderWidth: 2, pointRadius: 0, fill: false, tension: 0.25, order: 2 },
          { label: 'Fire activity index', data: blend(), borderColor: mix(0), borderWidth: 3.5, pointRadius: 0, pointHoverRadius: 6, fill: true, tension: 0.25, backgroundColor: mix(0, 0.12), order: 1 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          y: { min: 0, max: ymax, title: { display: true, text: 'Index (2000–2011 average = 100)' }, ticks: { maxTicksLimit: 6 } },
          x: { grid: { display: false }, ticks: { maxTicksLimit: 14, autoSkip: true } },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (it) => it[0].label + ' (modeled)'.slice(0, modeled ? 99 : 0),
              label: (it) => {
                const i = it.dataIndex;
                if (it.datasetIndex === 0) return `Raw: ${ES.fmt(r.raw[i], 0)}  (index ${ES.fmt(rawI[i], 0)})`;
                const showHarm = t >= 0.5;
                return `${showHarm ? 'Harmonized' : 'Raw'}: ${ES.fmt((showHarm ? r.harmonized : r.raw)[i], showHarm ? 1 : 0)}  (index ${ES.fmt(it.parsed.y, 0)})`;
              },
            },
          },
        },
      },
      plugins: [marker],
    });

    const jv = document.getElementById('jump-v');
    const fmtJ = (v) => (ES.isNum(v) ? (v >= 0 ? '+' : '') + ES.fmt(v, 1) + '%' : '—');
    function apply() {
      const ds = chart.data.datasets;
      ds[1].data = blend();
      ds[1].borderColor = mix(t);
      ds[1].backgroundColor = mix(t, 0.08 + 0.1 * t);
      ds[0].borderColor = mix(0, 0.55 * t);
      chart.update('none');
      box.style.setProperty('--t', t.toFixed(3));
      const v = ES.isNum(jRaw) && ES.isNum(jHarm) ? ES.lerp(jRaw, jHarm, t) : (t < 0.5 ? jRaw : jHarm);
      jv.textContent = fmtJ(v);
      jv.style.color = mix(t);
      scrub.value = Math.round(t * 100);
    }

    const rawRadio = document.getElementById('mode-raw'), harmRadio = document.getElementById('mode-harm');
    const scrub = document.getElementById('scrub');
    let raf = 0;
    function goTo(target) {
      const from = t; cancelAnimationFrame(raf);
      const t0 = performance.now(), dur = ES.reduced ? 0 : 1600;
      (function step(now) {
        const p = dur ? Math.min(1, (now - t0) / dur) : 1;
        t = ES.lerp(from, target, ES.ease(p));
        apply();
        if (p < 1) raf = requestAnimationFrame(step);
      })(t0);
    }
    rawRadio.addEventListener('change', () => rawRadio.checked && goTo(0));
    harmRadio.addEventListener('change', () => harmRadio.checked && goTo(1));
    scrub.addEventListener('input', () => {
      cancelAnimationFrame(raf);
      t = scrub.value / 100;
      (t >= 0.5 ? harmRadio : rawRadio).checked = true;
      apply();
    });
    apply();

    // draw-in on first view, then auto-demo once so the viewer sees the cliff heal
    t = 0; apply();
  };
})();
