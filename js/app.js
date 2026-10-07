/* EmberSync dashboard — shared helpers, KPI row, sensor split, biome table */
(function () {
  'use strict';
  const ES = (window.ES = window.ES || {});
  const REDUCED = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  ES.reduced = REDUCED;

  ES.BIOME_COLORS = { 1: '#b894ff', 2: '#4cd98a', 3: '#ffd23f', 4: '#ff6fa0' };
  ES.biomeColor = (id) => ES.BIOME_COLORS[id] || '#9aa4b8';

  ES.isNum = (v) => typeof v === 'number' && isFinite(v);
  ES.fmt = (v, d = 0, suffix = '') =>
    ES.isNum(v) ? v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }) + suffix : '—';
  ES.esc = (s) =>
    String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  ES.ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  ES.lerp = (a, b, t) => a + (b - a) * t;

  ES.tween = function (ms, onFrame, onDone) {
    if (REDUCED) { onFrame(1); onDone && onDone(); return; }
    const t0 = performance.now();
    (function step(now) {
      const p = Math.min(1, (now - t0) / ms);
      onFrame(ES.ease(p));
      if (p < 1) requestAnimationFrame(step); else onDone && onDone();
    })(t0);
  };

  ES.biomeName = (data, id) => {
    const b = (data.biomes || []).find((x) => x.class_id === id);
    return b ? b.name : 'Biome ' + id;
  };

  function countUp(el, target, digits, suffix) {
    if (!ES.isNum(target)) { el.textContent = '—'; return; }
    ES.tween(1400, (p) => { el.textContent = ES.fmt(target * p, digits, suffix); });
  }

  ES.renderHeader = function (d) {
    const m = d.meta || {};
    const n = document.getElementById('scope-n');
    if (n) n.textContent = ES.isNum(m.total_raw_records) ? ES.fmt(m.total_raw_records) : '—';
    const w = m.data_window || {};
    const days = document.getElementById('scope-days');
    if (days) days.textContent = ES.isNum(w.days) ? String(w.days) : '—';
    const win = document.getElementById('scope-win');
    if (win && w.start && w.end) win.textContent = 'Data window: ' + w.start + ' to ' + w.end + ' (UTC)';
    // Coverage is not uniform across biomes in every window; say so up front rather
    // than letting a one-day biome sit next to an eight-day one unremarked.
    const warn = document.getElementById('scope-warn');
    if (warn && m.coverage_warning) { warn.hidden = false; warn.textContent = m.coverage_warning; }
    const g = document.getElementById('gen-at');
    if (g && m.generated_at) g.textContent = 'Dataset generated ' + m.generated_at + '.';
    if (m.note && /placeholder/i.test(m.note)) {
      const err = document.getElementById('load-error');
      err.hidden = false;
      err.textContent = 'Showing PLACEHOLDER data. The values below are not results; the pipeline has not yet written the real dataset.';
    }
  };

  ES.renderKpis = function (d) {
    const m = d.meta || {};
    const tiles = [
      { k: 'Raw detections', v: m.total_raw_records, dg: 0, s: '', d: 'Every hot-spot ping the two satellites reported, duplicates included.', c: '' },
      { k: 'Physical fire events', v: m.total_fire_events, dg: 0, s: '', d: 'What is left after merging pings that are really the same fire.', c: 'cy' },
      { k: 'Inflation removed', v: m.inflation_removed_pct, dg: 1, s: '%', d: 'Share of the raw count that was artificial double-counting, not extra fire.', c: '' },
      { k: 'Cross-sensor validated', v: m.cross_sensor_matches, dg: 0, s: '', d: 'Fires seen by both MODIS and VIIRS on the same day: our ground truth for calibration.', c: 'cy' },
    ];
    const host = document.getElementById('kpis');
    host.innerHTML = tiles
      .map((t, i) => `<article class="kpi ${t.c} reveal" style="transition-delay:${i * 90}ms"><div class="kpi-k">${t.k}</div><div class="kpi-v" data-i="${i}">—</div><p class="kpi-d">${t.d}</p></article>`)
      .join('');
    host.querySelectorAll('.kpi').forEach((el) => el.classList.add('in'));
    tiles.forEach((t, i) => countUp(host.querySelector(`[data-i="${i}"]`), t.v, t.dg, t.s));

    const ss = d.sensor_split || {};
    const mo = ss.MODIS, vi = ss.VIIRS;
    const el = document.getElementById('sensor-split');
    if (!ES.isNum(mo) || !ES.isNum(vi) || mo + vi <= 0) { el.innerHTML = ''; return; }
    const tot = mo + vi;
    el.innerHTML = `<div class="ss"><div class="ss-bar" role="img" aria-label="MODIS ${ES.fmt(mo)} detections, VIIRS ${ES.fmt(vi)} detections"><i class="ss-m" style="width:0" data-w="${(mo / tot) * 100}"></i><i class="ss-v" style="width:0" data-w="${(vi / tot) * 100}"></i></div>
      <div class="ss-l"><span><i class="sw ss-m"></i>MODIS (1 km) <b>${ES.fmt(mo)}</b></span><span><i class="sw ss-v"></i>VIIRS (375 m) <b>${ES.fmt(vi)}</b></span>
      <span>VIIRS-to-MODIS ratio <b>${ES.isNum(ss.viirs_to_modis_ratio) ? ES.fmt(ss.viirs_to_modis_ratio, 2) + '×' : '—'}</b></span></div></div>`;
    requestAnimationFrame(() => requestAnimationFrame(() => el.querySelectorAll('[data-w]').forEach((i) => (i.style.width = i.dataset.w + '%'))));
  };

  ES.renderTable = function (d) {
    const tb = document.querySelector('#biome-table tbody');
    const bs = d.biomes || [];
    if (!bs.length) { tb.innerHTML = '<tr><td colspan="9">Per-biome results pending.</td></tr>'; return; }
    const F = ES.fmt;
    tb.innerHTML = bs
      .map((b) => {
        const c = b.calibration || {}, f = b.fit || {};
        const fit = ES.isNum(f.distribution_fit_pct) ? Math.max(0, Math.min(100, f.distribution_fit_pct)) : 0;
        const inf = ES.isNum(b.inflation_removed_pct) ? Math.max(0, Math.min(100, b.inflation_removed_pct)) : 0;
        return `<tr>
          <td data-label="Biome"><div class="bn"><i style="background:${ES.biomeColor(b.class_id)}"></i><span>${ES.esc(b.name)}<small>${ES.esc(b.region || '')}</small></span></div></td>
          <td class="num" data-label="Raw → events">${F(b.raw_records)} → ${F(b.fire_events)}</td>
          <td class="num" data-label="Optimal radius">${F(b.optimal_radius_km, 2)}<span class="u">km</span></td>
          <td class="num" data-label="Calibration exponent">${F(c.power_exponent, 2)}<span class="sub">w<sub>FRP</sub> ${F(c.w_frp, 2)}</span></td>
          <td class="num hi" data-label="Distribution fit">${F(f.distribution_fit_pct, 1, '%')}<span class="sub">median ratio ${F(f.median_ratio_before, 2)} &rarr; ${F(f.median_ratio_after, 2)}</span><span class="mini-bar"><i data-w="${fit}"></i></span></td>
          <td class="num" data-label="Per-fire skill">r ${F(f.per_fire_r_log10, 2)}<span class="sub">median err ${F(f.per_fire_median_rel_error_pct, 0, '%')}</span></td>
          <td class="num" data-label="Validation">${F(f.n_validation_pairs)}<span class="sub">${ES.esc(f.validation_split || '—')}</span></td>
          <td class="num" data-label="Cross-sensor matches">${F(b.cross_sensor_matches)}</td>
          <td class="num" data-label="Inflation removed">${F(b.inflation_removed_pct, 1, '%')}<span class="mini-bar em"><i data-w="${inf}"></i></span></td>
        </tr>`;
      })
      .join('');
    requestAnimationFrame(() => requestAnimationFrame(() => tb.querySelectorAll('[data-w]').forEach((i) => (i.style.width = i.dataset.w + '%'))));
  };

  ES.initReveal = function () {
    const els = document.querySelectorAll('.sec .card, .sec-head');
    els.forEach((e) => e.classList.add('reveal'));
    if (!('IntersectionObserver' in window)) { els.forEach((e) => e.classList.add('in')); return; }
    const io = new IntersectionObserver((es) => es.forEach((x) => { if (x.isIntersecting) { x.target.classList.add('in'); io.unobserve(x.target); } }), { threshold: 0.05 });
    els.forEach((e) => io.observe(e));
  };
})();
