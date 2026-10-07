/* Section 3 — Burning Activity Calendar (GitHub-style week grid, adaptive cell size) */
(function () {
  'use strict';
  const ES = window.ES;
  const DAY = 86400000;
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const STATUS = { NORMAL: 'Normal', ELEVATED_RISK: 'Elevated risk', CRITICAL_ANOMALY: 'Critical anomaly' };
  const ts = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ''); return m ? Date.UTC(+m[1], +m[2] - 1, +m[3]) : NaN; };
  const iso = (t) => new Date(t).toISOString().slice(0, 10);

  ES.renderCalendar = function (d) {
    const host = document.getElementById('cal');
    const tabs = document.getElementById('cal-tabs');
    const tip = document.getElementById('cal-tip');
    const note = document.getElementById('cal-note');
    const rows = (d.calendar || []).filter((r) => !isNaN(ts(r.date)));
    document.getElementById('cal-legend').innerHTML =
      '<li>Fewer<span class="sw-c l1"></span><span class="sw-c l2"></span><span class="sw-c l3"></span><span class="sw-c l4"></span>More events</li>' +
      '<li><span class="sw-c el"></span>&#9650; Elevated risk</li><li><span class="sw-c cr"></span>&#9670; Critical anomaly</li><li><span class="sw-c nd"></span>No record</li>';
    if (!rows.length) { host.innerHTML = '<p class="caption">Calendar data pending.</p>'; tabs.innerHTML = ''; return; }

    const byKey = new Map(), maxEv = {};
    rows.forEach((r) => {
      byKey.set(r.class_id + '|' + iso(ts(r.date)), r);
      if (ES.isNum(r.events)) maxEv[r.class_id] = Math.max(maxEv[r.class_id] || 0, r.events);
    });
    const t0 = Math.min.apply(null, rows.map((r) => ts(r.date)));
    const t1 = Math.max.apply(null, rows.map((r) => ts(r.date)));
    const spanDays = Math.round((t1 - t0) / DAY) + 1;
    const strip = spanDays <= 31; // sparse data: one readable row of days instead of a mostly-empty week grid
    const start = strip ? t0 : t0 - new Date(t0).getUTCDay() * DAY;
    const end = strip ? t1 : t1 + (6 - new Date(t1).getUTCDay()) * DAY;
    const cols = strip ? spanDays : Math.round((end - start) / DAY + 1) / 7;
    const NR = strip ? 1 : 7;
    const size = strip ? 'strip' : cols <= 20 ? 'mid' : 'dense';

    const ids = [];
    (d.biomes || []).forEach((b) => ids.push(b.class_id));
    rows.forEach((r) => { if (ids.indexOf(r.class_id) < 0) ids.push(r.class_id); });
    let sel = 'all';

    function level(ev, id) {
      if (!ES.isNum(ev) || ev <= 0) return 0;
      const r = ev / (maxEv[id] || ev);
      return r < 0.25 ? 1 : r < 0.5 ? 2 : r < 0.75 ? 3 : 4;
    }

    function block(id) {
      let h = '<div class="cal-block"><div class="cal-title"><i style="background:' + ES.biomeColor(id) + '"></i>' + ES.esc(ES.biomeName(d, id)) +
        '<small>' + ES.fmt(rows.filter((r) => r.class_id === id).length) + ' days with data</small></div><div class="cal-scroll">' +
        '<div class="cal-grid ' + size + '" style="--cols:' + cols + '" role="grid" aria-label="' + ES.esc(ES.biomeName(d, id)) + ' burning activity">';
      // month labels row
      h += '<span></span>';
      let lastM = -1;
      for (let c = 0; c < cols; c++) {
        const dt = new Date(start + c * (strip ? 1 : 7) * DAY);
        const m = dt.getUTCMonth();
        const txt = strip ? DOW[dt.getUTCDay()] + ' ' + dt.getUTCDate() + ' ' + MON[m] : size === '' ? (c === 0 || m !== lastM ? MON[m] + ' ' + dt.getUTCDate() : '') : (m !== lastM ? MON[m] : '');
        lastM = m;
        h += '<span class="cal-ml" style="grid-column:' + (c + 2) + ';grid-row:1">' + txt + '</span>';
      }
      for (let r = 0; r < NR; r++) {
        h += strip ? '<span></span>' : '<span class="cal-dl" style="grid-row:' + (r + 2) + '">' + (size === 'dense' ? (r % 2 === 1 ? DOW[r] : '') : DOW[r]) + '</span>';
        for (let c = 0; c < cols; c++) {
          const t = start + (strip ? c : c * 7 + r) * DAY, key = iso(t), rec = byKey.get(id + '|' + key);
          const pos = 'grid-column:' + (c + 2) + ';grid-row:' + (r + 2);
          const inRange = t >= t0 && t <= t1;
          if (!rec) {
            h += '<span class="cell ' + (inRange ? 'nodata' : 'empty') + '" style="' + pos + '"' + (inRange ? ' title="' + key + ': no record"' : '') + '></span>';
            continue;
          }
          const L = level(rec.events, id), st = rec.status || 'NORMAL';
          const glyph = st === 'CRITICAL_ANOMALY' ? '<span class="g" aria-hidden="true">!!</span>' : st === 'ELEVATED_RISK' ? '<span class="g" aria-hidden="true">&#9650;</span>' : '';
          const aria = key + ', ' + ES.biomeName(d, id) + ', ' + ES.fmt(rec.events) + ' events, Z-score ' + ES.fmt(rec.z_score, 2) + ', ' + (STATUS[st] || st);
          h += '<button type="button" class="cell s-' + st + '" data-l="' + L + '" style="' + pos + '" data-k="' + key + '" data-b="' + id + '" aria-label="' + ES.esc(aria) + '">' +
            glyph + '<span class="dn">' + new Date(t).getUTCDate() + '</span><span class="ev">' + (ES.isNum(rec.events) ? ES.fmt(rec.events) : '—') + '</span></button>';
        }
      }
      return h + '</div></div></div>';
    }

    function render() {
      const show = sel === 'all' ? ids : [sel];
      host.innerHTML = show.map(block).join('');
      tabs.querySelectorAll('.tab').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.id === String(sel))));
    }

    tabs.innerHTML = '<button type="button" class="tab" data-id="all" aria-pressed="true">All biomes</button>' +
      ids.map((id) => '<button type="button" class="tab" data-id="' + id + '" aria-pressed="false" style="--c:' + ES.biomeColor(id) + '"><i></i>' + ES.esc(ES.biomeName(d, id)) + '</button>').join('');
    tabs.addEventListener('click', (e) => {
      const b = e.target.closest('.tab'); if (!b) return;
      sel = b.dataset.id === 'all' ? 'all' : +b.dataset.id; hideTip(); render();
    });

    function showTip(cell) {
      const rec = byKey.get(cell.dataset.b + '|' + cell.dataset.k); if (!rec) return;
      const st = rec.status || 'NORMAL';
      tip.innerHTML = '<b>' + ES.esc(rec.date) + '</b><dl><dt>Biome</dt><dd>' + ES.esc(ES.biomeName(d, rec.class_id)) + '</dd><dt>Fire events</dt><dd>' + ES.fmt(rec.events) +
        '</dd><dt>FRP (raw)</dt><dd>' + ES.fmt(rec.frp, 0) + ' MW</dd><dt>FRP (harmonized)</dt><dd>' + ES.fmt(rec.harmonized_frp, 0) + ' MW</dd><dt>Z-score</dt><dd>' + ES.fmt(rec.z_score, 2) +
        '</dd></dl><div class="st ' + st + '">' + (st === 'CRITICAL_ANOMALY' ? '&#9670; ' : st === 'ELEVATED_RISK' ? '&#9650; ' : '') + (STATUS[st] || st).toUpperCase() + '</div>';
      tip.hidden = false;
      const r = cell.getBoundingClientRect(), tw = tip.offsetWidth, th = tip.offsetHeight;
      let x = r.left + r.width / 2 - tw / 2, y = r.top - th - 10;
      if (y < 8) y = r.bottom + 10;
      x = Math.max(8, Math.min(x, window.innerWidth - tw - 8));
      tip.style.left = x + 'px'; tip.style.top = y + 'px';
    }
    function hideTip() { tip.hidden = true; }
    host.addEventListener('mouseover', (e) => { const c = e.target.closest('.cell[data-k]'); c ? showTip(c) : hideTip(); });
    host.addEventListener('mouseleave', hideTip);
    host.addEventListener('focusin', (e) => { const c = e.target.closest('.cell[data-k]'); c && showTip(c); });
    host.addEventListener('focusout', hideTip);
    window.addEventListener('scroll', hideTip, { passive: true });
    host.addEventListener('click', (e) => { const c = e.target.closest('.cell[data-k]'); c && showTip(c); });

    note.textContent = spanDays + '-day window shown (' + iso(t0) + ' to ' + iso(t1) + '). Cell brightness is scaled within each biome. Flags come from each day\'s Z-score against that biome\'s baseline' +
      (spanDays < 60 ? '; with a short window the baseline is limited, so treat flags as a demonstration of the engine. The grid expands to a full 365-day year as the archive is ingested.' : '.');
    render();
  };
})();
