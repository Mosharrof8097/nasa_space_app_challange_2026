/* Loads data/dashboard_data.json (falls back to data/dashboard_data.js for file:// use) and renders every section. */
(function () {
  'use strict';
  const ES = window.ES;

  function loadScriptData() {
    return new Promise((res, rej) => {
      if (window.EMBERSYNC_DATA) return res(window.EMBERSYNC_DATA);
      const s = document.createElement('script');
      s.src = 'data/dashboard_data.js';
      s.onload = () => (window.EMBERSYNC_DATA ? res(window.EMBERSYNC_DATA) : rej(new Error('empty')));
      s.onerror = () => rej(new Error('missing'));
      document.head.appendChild(s);
    });
  }

  function load() {
    return fetch('data/dashboard_data.json', { cache: 'no-store' })
      .then((r) => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .catch(() => loadScriptData());
  }

  function safe(name, fn) {
    try { fn(); } catch (e) { console.error('[EmberSync] ' + name + ' failed:', e); }
  }

  function fail() {
    const err = document.getElementById('load-error');
    err.hidden = false;
    err.innerHTML = 'Could not load <code>data/dashboard_data.json</code>. If you opened this file directly, run <code>python3 -m http.server</code> inside the <code>webapp/</code> folder and visit <code>http://localhost:8000</code> (or run <code>python3 make_offline_data.py</code> once).';
  }

  ES.initReveal();
  load().then((d) => {
    safe('header', () => ES.renderHeader(d));
    safe('kpis', () => ES.renderKpis(d));
    safe('timeline', () => ES.renderTimeline(d));
    safe('map', () => ES.renderMap(d));
    safe('calendar', () => ES.renderCalendar(d));
    safe('table', () => ES.renderTable(d));
    safe('ga', () => ES.renderGA(d));
    document.documentElement.setAttribute('data-ready', '1');
  }).catch((e) => { console.warn('[EmberSync] data load failed', e); fail(); });
})();
