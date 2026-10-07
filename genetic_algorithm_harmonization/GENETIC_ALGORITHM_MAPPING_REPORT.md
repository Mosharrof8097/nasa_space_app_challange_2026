# Stage 2 — Multi-Objective Genetic Algorithm Calibration Report

**Generated:** 2026-10-07 19:08:17  
**Population:** 50 · **Generations:** 30 · **Selection:** tournament (k=3) · **Crossover:** arithmetic (Pc=0.85) · **Mutation:** Gaussian (Pm=0.15) · **Elitism:** 2  
**Seed:** 42 (runs are reproducible)

---

## 1. What is being optimised, and against what

Fires that **both** satellites detected on the same day in the same place give
real paired observations: a VIIRS measurement and a MODIS measurement of one
physical fire. Those pairs are the supervision signal.

The calibration learns a power-law transform

```
MODIS_FRP  ~=  w_frp * VIIRS_FRP^p  +  w_brightness * VIIRS_brightness * (VIIRS_pixels / cluster_scale)
```

Only VIIRS-side observables enter the predictor, so the MODIS target never leaks
into its own prediction. Accuracy is reported on a held-out 30% of pairs that the
genetic algorithm never saw while evolving.

### Why the objective is distributional, not per-fire

Measured on our own paired fires, the per-fire correlation between the two
instruments is only **r = 0.20 to 0.67** in log space, and the best achievable
power law explains almost none of the per-fire variance (R² between -0.04 and
0.14). That is a property of the instruments, not a defect in the fit: a single
fire's FRP depends on viewing geometry, overpass time and sub-pixel heterogeneity
that the two sensors do not resolve identically. **No transform of VIIRS FRP can
accurately predict an individual MODIS FRP**, and any project claiming otherwise
should be asked for its holdout numbers.

What *is* stable is the distribution. The median MODIS/VIIRS FRP ratio sits in a
narrow **1.04 to 1.43** band across all four biomes — an independent confirmation,
from our own data, of the ~20% systemic offset reported by Li et al. (2018).

So the energy objective performs **quantile mapping**: it matches the 10th through
90th percentiles of the harmonized VIIRS distribution onto the MODIS distribution,
scored in log space so each decade of fire intensity counts equally. Quantile
mapping is the standard remote-sensing approach for cross-sensor harmonization, and
distributional accuracy is what the Burning Activity Calendar actually consumes —
the calendar aggregates fires per day and per region rather than tracking
individual fires.

Two objectives are optimised together:

| Objective | Governed by | Meaning |
| :--- | :--- | :--- |
| Distributional energy (weight 0.6) | `w_frp`, `power_exponent`, `w_brightness`, `cluster_scale` | Land the harmonized VIIRS FRP distribution on the MODIS distribution |
| Count parity (weight 0.4) | `radius_km` | Bring the consolidated VIIRS event count in line with the MODIS event count |

Count parity is what makes the radius gene meaningful. Too small a radius leaves
VIIRS fragmented across many events (ratio >> 1); too large a radius over-merges
distinct fires (ratio < 1). Scoring the log of the ratio keeps the optimum in the
interior of the search range instead of pushing it to a boundary.

---

## 2. Evolved parameters and accuracy

| Biome | Radius | w_frp | exponent | Fitness | Distribution fit (holdout) | Median ratio before → after | Paired fires | Split |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **Montane & Hills** | 1.20 km | 1.2234 | 0.9923 | 75.1523 | 82.8% | 1.5727 → 0.9149 | 36 | held-out 30% |
| **Dense Rainforest** | 0.80 km | 0.6736 | 0.887 | 80.5413 | 92.25% | 1.178 → 1.028 | 1,098 | held-out 30% |
| **Agricultural Plains** | 1.50 km | 0.2 | 0.8008 | 68.7107 | 89.49% | 0.9389 → 0.906 | 17 | in-sample (too few paired fires for a holdout) |
| **Savannas & Grasslands** | 1.50 km | 0.7928 | 1.017 | 88.5414 | 73.85% | 1.2521 → 0.6025 | 30 | held-out 30% |

### Per-fire skill (reported for transparency, not optimised for)

| Biome | Pearson r (log10) | Median rel. error | R² | 
| :--- | ---: | ---: | ---: |
| **Montane & Hills** | 0.78 | 40.67% | 0.6939 |
| **Dense Rainforest** | 0.4858 | 60.6% | 0.0369 |
| **Agricultural Plains** | 0.3282 | 63.35% | -0.9738 |
| **Savannas & Grasslands** | 0.1874 | 67.49% | -3.3074 |

### Count parity at the evolved optimum

| Biome | VIIRS : MODIS event ratio | Consolidated events | Mean pixels/event |
| :--- | ---: | ---: | ---: |
| **Montane & Hills** | 3.4121 | 760 | 3.76 |
| **Dense Rainforest** | 2.1344 | 31,355 | 2.42 |
| **Agricultural Plains** | 5.2787 | 366 | 1.92 |
| **Savannas & Grasslands** | 0.7525 | 2,388 | 1.55 |

---

## 3. Radius sweep

Every candidate radius was clustered in full before evolution began, so the
genetic algorithm selects among real clustering outcomes rather than a free
parameter with no effect.

### Montane & Hills

| Radius (km) | Events | Paired fires | VIIRS:MODIS event ratio | Mean px/event |
| ---: | ---: | ---: | ---: | ---: |
| 0.6 | 1,073 | 154 | 2.5982 | 2.67 |
| 0.7 | 940 | 140 | 2.4951 | 3.04 |
| 0.8 | 898 | 144 | 2.6181 | 3.19 |
| 0.9 | 846 | 129 | 2.7645 | 3.38 |
| 1.0 | 802 | 123 | 3.057 | 3.57 |
| 1.1 | 777 | 123 | 3.2857 | 3.68 |
| 1.2 | 760 | 118 | 3.4121 | 3.76 |
| 1.3 | 743 | 121 | 3.4767 | 3.85 |
| 1.4 | 737 | 120 | 3.5105 | 3.88 |
| 1.5 | 720 | 117 | 3.6243 | 3.97 |
| 1.6 | 721 | 118 | 3.6611 | 3.97 |

### Dense Rainforest

| Radius (km) | Events | Paired fires | VIIRS:MODIS event ratio | Mean px/event |
| ---: | ---: | ---: | ---: | ---: |
| 0.6 | 36,688 | 3,539 | 2.2657 | 2.07 |
| 0.7 | 33,354 | 3,613 | 2.1531 | 2.28 |
| 0.8 | 31,355 | 3,659 | 2.1344 | 2.42 |
| 0.9 | 29,799 | 3,676 | 2.15 | 2.55 |
| 1.0 | 28,171 | 3,662 | 2.296 | 2.7 |
| 1.1 | 26,627 | 3,651 | 2.5142 | 2.85 |
| 1.2 | 25,721 | 3,662 | 2.6217 | 2.95 |
| 1.3 | 25,011 | 3,682 | 2.6626 | 3.04 |
| 1.4 | 24,494 | 3,658 | 2.712 | 3.1 |
| 1.5 | 23,940 | 3,652 | 2.753 | 3.17 |
| 1.6 | 23,585 | 3,675 | 2.7662 | 3.22 |

### Agricultural Plains

| Radius (km) | Events | Paired fires | VIIRS:MODIS event ratio | Mean px/event |
| ---: | ---: | ---: | ---: | ---: |
| 0.6 | 446 | 16 | 5.6 | 1.57 |
| 0.7 | 421 | 17 | 5.6364 | 1.67 |
| 0.8 | 408 | 18 | 5.5538 | 1.72 |
| 0.9 | 407 | 17 | 5.625 | 1.72 |
| 1.0 | 396 | 17 | 5.7705 | 1.77 |
| 1.1 | 388 | 17 | 5.6393 | 1.81 |
| 1.2 | 389 | 17 | 5.6557 | 1.8 |
| 1.3 | 378 | 17 | 5.4754 | 1.85 |
| 1.4 | 373 | 17 | 5.3934 | 1.88 |
| 1.5 | 366 | 17 | 5.2787 | 1.92 |
| 1.6 | 365 | 17 | 5.2623 | 1.92 |

### Savannas & Grasslands

| Radius (km) | Events | Paired fires | VIIRS:MODIS event ratio | Mean px/event |
| ---: | ---: | ---: | ---: | ---: |
| 0.6 | 3,026 | 54 | 0.6435 | 1.22 |
| 0.7 | 2,948 | 64 | 0.6334 | 1.26 |
| 0.8 | 2,856 | 72 | 0.6267 | 1.3 |
| 0.9 | 2,807 | 75 | 0.6292 | 1.32 |
| 1.0 | 2,712 | 84 | 0.6496 | 1.37 |
| 1.1 | 2,562 | 87 | 0.7013 | 1.45 |
| 1.2 | 2,492 | 88 | 0.7269 | 1.49 |
| 1.3 | 2,455 | 92 | 0.7374 | 1.51 |
| 1.4 | 2,411 | 94 | 0.7505 | 1.54 |
| 1.5 | 2,388 | 97 | 0.7525 | 1.55 |
| 1.6 | 2,339 | 102 | 0.7612 | 1.58 |

---

## 4. Scope and limitations

- Calibration is fitted on the benchmark window currently ingested, not the full
  multi-year archive. Coefficients should be re-evolved once the archive is loaded.
- Biomes with few paired fires are reported in-sample and flagged as such in the
  `split` column above; treat those coefficients as provisional.
- MODIS is treated as the harmonization baseline because it defines the longer
  record (2000 onward). This follows the convention in the multi-decadal
  harmonization literature and is a choice, not a statement that MODIS is more
  accurate — Li et al. (2018) show MODIS FRP itself inflates toward swath edges.
- **This stage harmonizes distributions, not individual fires.** Outputs are valid
  for aggregated products such as the Burning Activity Calendar. They should not be
  used to restate the FRP of one specific fire.
- A scan-angle term is not yet included. Li et al. (2018) attribute much of the
  residual FRP difference to viewing geometry, so adding `scan`/`track` as
  predictors is the clearest next improvement, and is the most likely route to
  recovering genuine per-fire skill.
- Paired fires come from a single overlap window. A longer archive will give far
  more pairs per biome, which matters most for Agricultural Plains and Savannas.
