#!/usr/bin/env python3
"""Optional: wraps data/dashboard_data.json as data/dashboard_data.js so index.html also works when
opened by double-click (browsers block fetch() on file:// URLs). Re-run after the JSON is regenerated."""
import json, pathlib
d = pathlib.Path(__file__).resolve().parent / "data"
data = json.loads((d / "dashboard_data.json").read_text(encoding="utf-8"))
(d / "dashboard_data.js").write_text("window.EMBERSYNC_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
print("wrote", d / "dashboard_data.js")
