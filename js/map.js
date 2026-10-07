/* Section 2 — Leaflet map with biome filter, FRP sizing toggle and zoom-aware thinning */
(function () {
  'use strict';
  const ES = window.ES;
  const MAX_MARKERS = 2500;

  ES.renderMap = function (d) {
    if (!window.L) throw new Error('Leaflet not loaded (CDN unreachable?)');
    const pts = (d.fire_points || []).filter((p) => ES.isNum(p.lat) && ES.isNum(p.lon));
    const status = document.getElementById('map-status');
    const map = L.map('map', { worldCopyJump: true, minZoom: 2, zoomSnap: 0.5, attributionControl: true }).setView([12, 15], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors', subdomains: 'abc', maxZoom: 12, className: 'dark-tiles',
    }).addTo(map);
    const layer = L.layerGroup().addTo(map);

    // Shared reference so raw vs harmonized sizes are comparable: 95th percentile of raw FRP.
    const frps = pts.map((p) => p.frp).filter(ES.isNum).sort((a, b) => a - b);
    const ref = frps.length ? Math.max(frps[Math.floor(frps.length * 0.95)] || frps[frps.length - 1], 1) : 1;
    const radius = (v) => (ES.isNum(v) ? 2 + 7 * Math.sqrt(Math.min(v, ref * 1.6) / ref) : 2.5);

    // biome chips
    const ids = [];
    (d.biomes || []).forEach((b) => ids.push(b.class_id));
    pts.forEach((p) => { if (ids.indexOf(p.class_id) < 0) ids.push(p.class_id); });
    const active = new Set(ids);
    const host = document.getElementById('map-biomes');
    ids.forEach((id) => {
      const n = pts.filter((p) => p.class_id === id).length;
      const lab = document.createElement('label');
      lab.className = 'bchip';
      lab.style.setProperty('--c', ES.biomeColor(id));
      lab.innerHTML = `<input type="checkbox" checked value="${id}"><span><i></i>${ES.esc(ES.biomeName(d, id))} <small style="opacity:.7">${ES.fmt(n)}</small></span>`;
      lab.querySelector('input').addEventListener('change', (e) => { e.target.checked ? active.add(id) : active.delete(id); draw(); });
      host.appendChild(lab);
    });

    let mode = 'frp';
    const seg = document.getElementById('map-size');
    seg.querySelectorAll('input').forEach((i) => i.addEventListener('change', () => { mode = i.value; seg.classList.toggle('harm', mode === 'harmonized_frp'); draw(); }));

    function popup(p, hidden) {
      const yes = p.cross_sensor ? '<span class="yes">Yes, both satellites</span>' : 'No, single sensor';
      return `<div class="pop"><h4><span class="bn"><i style="background:${ES.biomeColor(p.class_id)};width:10px;height:10px;border-radius:50%;display:inline-block"></i></span>${ES.esc(ES.biomeName(d, p.class_id))}</h4><dl>
        <dt>Date</dt><dd>${ES.esc(p.date || '—')}</dd><dt>Sensor</dt><dd>${ES.esc(p.sensor || '—')}</dd>
        <dt>Raw FRP</dt><dd>${ES.fmt(p.frp, 1)} MW</dd><dt>Harmonized FRP</dt><dd>${ES.fmt(p.harmonized_frp, 1)} MW</dd>
        <dt>Pixels merged</dt><dd>${ES.fmt(p.pixels)}</dd><dt>Both confirmed</dt><dd>${yes}</dd></dl>
        ${hidden > 0 ? `<p class="hid">+${ES.fmt(hidden)} nearby detections hidden at this zoom. Zoom in to reveal.</p>` : ''}</div>`;
    }

    function draw() {
      layer.clearLayers();
      let list = pts.filter((p) => active.has(p.class_id));
      const total = list.length;
      const b = map.getBounds().pad(0.25);
      const inView = list.filter((p) => b.contains([p.lat, p.lon]));
      let shown = inView, thinned = false;
      const hiddenAt = new Map();
      if (inView.length > MAX_MARKERS) {
        thinned = true;
        const cell = 16 / Math.pow(2, map.getZoom()); // degrees
        const best = new Map();
        inView.forEach((p) => {
          const k = Math.floor(p.lat / cell) + ':' + Math.floor(p.lon / cell);
          const cur = best.get(k);
          const v = ES.isNum(p[mode]) ? p[mode] : -1;
          if (!cur) best.set(k, { p, v, n: 0 });
          else { cur.n++; if (v > cur.v) { cur.p = p; cur.v = v; } }
        });
        shown = [];
        best.forEach((o) => { shown.push(o.p); hiddenAt.set(o.p, o.n); });
      }
      // draw large first so small ones remain clickable
      shown.slice().sort((a, b) => (b[mode] || 0) - (a[mode] || 0)).forEach((p) => {
        const c = ES.biomeColor(p.class_id);
        const m = L.circleMarker([p.lat, p.lon], {
          radius: radius(p[mode]), color: p.cross_sensor ? '#ffffff' : c, weight: p.cross_sensor ? 2 : 1,
          fillColor: c, fillOpacity: 0.55, opacity: p.cross_sensor ? 0.95 : 0.8,
        });
        m.bindPopup(() => popup(p, hiddenAt.get(p) || 0), { maxWidth: 260 });
        m.addTo(layer);
      });
      status.textContent = pts.length
        ? `Showing ${ES.fmt(shown.length)} of ${ES.fmt(total)} detections in the selected biomes${thinned ? ' (thinned to the strongest per grid cell for speed; zoom in for more)' : ''}. Marker size uses ${mode === 'frp' ? 'raw' : 'harmonized'} FRP.`
        : 'No fire points are present in the dataset yet.';
    }

    map.on('moveend zoomend', draw);
    draw();
    if (pts.length > 1) {
      const bounds = L.latLngBounds(pts.map((p) => [p.lat, p.lon]));
      if (bounds.isValid()) { /* keep a global view: this is a global benchmark */ }
    }
    setTimeout(() => map.invalidateSize(), 300);
  };
})();
