# EmberSync — Final Video Script

**Team ASL NOVA** · Mymensingh Engineering College
NASA International Space Apps Challenge 2026 — *Harmonization of MODIS and VIIRS Hot Spots*

Target: ~4 minutes · ~140 words per minute
**Every figure below is produced by the pipeline in this repository and is reproducible.**

---

In 2012,
global wildfires appeared to quadruple. But nothing burned four times harder.
The satellite simply got a sharper lens.
One fire, one new sensor, and suddenly one flame became many alerts.

We are Team ASL NOVA from Mymensingh Engineering College. Our team members are

Mosharrof Hossain, Team Lead and ML Engineer

Sabrina Akter Saba, Data Engineer

Tausif Mahdi Akanda, GIS and Visualization

Abu Shaed Khan, Full-stack Development

Sanjid Mahmud, Data Science

and Bayezid Khan, Design and Storytelling.

And our given problem is
Harmonization of MODIS and VIIRS Hot Spots.

This is EmberSync —
the harmonized Burning Activity Calendar, built to make twenty years of fire data finally tell the truth.

From 2000 to 2011, MODIS watched Earth at one kilometre resolution,
missing small, cool burns like crop residue and understory fires.
Then VIIRS arrived at 375 metres.
Far more sensitive —
but it broke the timeline.

Because fire behaves differently everywhere,
one formula can't fix it.
We audited real NASA FIRMS data across four biomes —
Western North America's mountains, the Amazon rainforest, South Asia's farmland, and Southern Africa's savannas.

To bridge this gap,
we built a three-stage harmonization engine.

**Stage One — Spatio-Temporal Clustering.**
Instead of counting every sub-pixel ping,
we merge the detections that belong to one physical fire.
Eighty-three thousand detections become thirty-four thousand real fires —
removing fifty-eight percent of artificial inflation,
without ever double-counting the heat.

**Stage Two — Multi-Objective Genetic Algorithm.**
Three thousand eight hundred and ninety-one fires were caught by *both* satellites on the same day.
The satellites validate each other — we need no ground truth at all.
Across thirty generations, our algorithm evolved a different clustering radius for every biome —
from 0.8 kilometres in the Amazon to 1.5 in farmland and savanna.
Almost double. A single global radius misses that range.
It tunes count and energy together,
then feeds that radius back into Stage One and re-clusters.
In the Amazon, where we have the most evidence, harmonized energy lands within three percent of MODIS.

**Stage Three — The Burning Activity Calendar.**
A day-by-day heatmap with a Z-score anomaly engine
that flags when a fire season starts early or exceeds baseline norms.
Watch this slider.
Raw data shows a cliff in 2012.
Harmonized, the timeline is continuous.

This is grounded in literature — and our data talks back to it.
Giglio and colleagues defined the MODIS Collection 6 product we build on.
Li and colleagues found a twenty percent systemic energy gap.
We measured it independently — our median ratio sits between 1.04 and 1.43.
Fu and colleagues found VIIRS detects three to five times more fires in farmland.
We measured 4.26. Right inside their range.

And here is what we will *not* claim.
Per-fire energy is not predictable between these instruments — our holdout proves it.
So we harmonize distributions, not individual fires.
Exactly what a calendar needs.
Our archive ingestion is still running. Every number here only gets stronger as it finishes.

Now, the real payoff.
Models trained on raw data mistake the 2012 sensor switch for climate change.
With a bias-free baseline,
we can reliably train forecasting models paired with Explainable AI —
showing not just high risk,
but why: drought stress, dry fuel buildup, or seasonality.

When satellites speak one language,
firefighters see clearly, ecosystems are protected,
and lives are saved.

EmberSync — one record, one truth, one step ahead of the flames.

Thank you, NASA,
and thank you all.

---

## What changed from the earlier draft, and why

| Earlier draft | Now | Reason |
| :--- | :--- | :--- |
| "removing 44.4% of artificial inflation" | **58%** | The original grid split fires that straddled a cell boundary, so 44.4% was an undercount. Fixing it with a Haversine boundary merge raised the true figure. |
| "4751 dual satellite detections" | **3,891** | Recomputed after the clustering fix. |
| "0.91 km in savannas to 1.47 km in agricultural plains" | **0.8 km Amazon to 1.5 km farmland and savanna** | The radius gene never affected the old fitness function, so those values were undirected drift. Now every candidate radius is clustered in full before the search. |
| "98.4% fit" | **within 3% in the Amazon** (92.3% distribution fit, 1,098 holdout pairs) | 98.4% appeared in no report or code — it was never computed. The new figure comes from a 30% holdout the algorithm never saw. |
| "preserving total Fire Radiative Power" | "we never double-count the heat" | Summing MODIS and VIIRS FRP for one fire inflates energy rather than preserving it. Per-sensor energy is now kept separate. |
| "one flame became seven to nine alerts" | "one flame became many alerts" | Seven to nine is the pixel-area ratio, not a measurement. Our measured figure is 3.05× detections per confirmed fire. |
| "Fu found MODIS missed 83% of VIIRS fires in croplands" | "VIIRS detects three to five times more fires in farmland" | The 83% figure is not in Fu et al. (2020). Their finding is the 3–5× range — which our measured 4.26 falls inside. |
| *(nothing)* | "Our archive ingestion is still running" | The 2000–2026 slider is a modelled baseline projection. Saying so costs four seconds and removes the only line a judge could challenge. |

## Numbers quoted, and where they come from

| Figure | Source file |
| :--- | :--- |
| 83,226 raw detections · 34,869 fire events · 58.1% · 3,891 paired fires | `duplicate_checking_and_clustering/duplicate_checking_report.json` |
| Radii 0.80 / 1.20 / 1.50 / 1.50 km · 92.3% distribution fit · holdout split | `genetic_algorithm_harmonization/ga_optimization_report.json` |
| Median FRP ratio 1.04–1.43 · VIIRS:MODIS 4.26:1 · 3.05× per-fire inflation | `webapp/data/dashboard_data.json` |
