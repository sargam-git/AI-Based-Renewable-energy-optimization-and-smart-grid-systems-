# Executed validation record

Date: **1 November 2026**  
Environment used here: **Python 3.13.16**, **Node.js 20.20.2**, npm 10.8.2, Chromium via Playwright 1.56.1.

This record describes checks actually executed against the implementation. It is not a certification, a hardware test, or evidence of real-world forecasting accuracy.

## Summary

| Check | Result | Evidence |
|---|---:|---|
| Backend Pytest suite | **79 passed** | `docs/validation/backend-tests.log` |
| Frontend Vitest suite | **8 passed** | `docs/validation/frontend-tests.log` |
| Playwright browser integration | **7 passed** | `docs/validation/browser-tests.log` |
| Vite production build | **Passed** | `docs/validation/frontend-build.log` |
| npm audit | **0 vulnerabilities** | Executed after the final frontend build |
| Python dependency consistency | **Passed** | `backend/.venv/bin/pip check` → no broken requirements |
| Seven-scenario engine validation | **7 optimal solves** | `docs/scenario-validation.json` |
| Launcher smoke test | **Passed** | `./run.sh` installed/checked dependencies, prepared the database, and started ports 5173 and 8000 |
| Clean demo state | **Normal, 2026-11-01 10:00, 744 kWh / 62% SOC** | `/api/simulation/state` after validation-data reset |
| Final browser smoke | **No page errors; mobile Simulation width 390/390 px** | Desktop/mobile screenshots in `docs/screenshots/` |

Backend tests use a temporary database and freshly trained 60-day models. They do not modify the demonstration database. The included demonstration models were trained on the full 120-day synthetic dataset.

## Commands executed

From the project root:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  backend/.venv/bin/python -m pytest backend/tests -q

cd frontend
npm test
npm run build
npm audit
npm run test:e2e   # both application servers running
```

Scenario comparison, from `backend/`:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  .venv/bin/python -m app.utils.validation > ../docs/scenario-validation.json
```

The scenario utility calls the real forecasting/optimization/monitoring pipeline from a fixed initial state. It does not write those comparison runs into simulation history.

## What the tests cover

- Raw-data cleaning, physical bounds, missing values, chronological splitting, feature construction, model persistence and prediction.
- Solar/wind physical behavior, including night output and wind cut-in/rated/cut-out behavior.
- Demand extremes, sector allocation, essential-first scarcity policy and served-load clamping.
- Battery energy conservation, charge/discharge efficiency, SOC bounds, power limits, full/minimum reserve, and no simultaneous charge/discharge.
- Renewable/load balance, no grid charging, import/export exclusivity and limits, terminal-energy floor, per-hour transformer screening, curtailment and explicit unserved energy.
- All seven named scenarios through both the optimization engine and API.
- Explicit post-inference demand multiplication: the total and every consumer sector scale by the requested factor.
- Solver failure returns an error instead of fabricating a dispatch plan.
- Simulated voltage/frequency/overload abnormalities, electrical identities, Isolation Forest scoring and heuristic equipment risk.
- API validation, invalid CSV rejection, compatible CSV prediction, maintenance creation/completion, anomaly acknowledgement and report downloads.
- Clock advancement with carried battery inventory, reset behavior, SQLite persistence across sessions and a separate Python process.
- All ten frontend pages, interactive charts/topology/theme/clock, scenario application, editable simulation inputs, maintenance workflow, CSV upload/download and mobile navigation.
- Horizontal-overflow checks on desktop pages and the 390 px mobile Simulation page.

## Held-out model results

Chronological split of the included 2,880-row synthetic dataset: 70% train, 15% validation, 15% untouched test. The registry records 2,015 usable training rows, 433 validation rows and 432 test rows after target cleaning.

| Target | Selected model | MAE (kW) | RMSE (kW) | R² | 24-hour naive MAE (kW) |
|---|---|---:|---:|---:|---:|
| Solar | XGBoost, depth 3 | 2.8221 | 6.8968 | 0.9981 | 11.2390 |
| Wind | Random Forest, depth 14 | 6.0507 | 8.1424 | 0.9845 | 26.5794 |
| Demand | Random Forest, depth 14 | 7.3222 | 19.8490 | 0.8892 | **5.0267** |

Important interpretation:

- These are **synthetic holdout** results. High solar R² is expected because the generator follows a known physical relationship with modest noise.
- The demand model beats the linear candidate but **does not beat the simple 24-hour seasonal baseline** on this dataset. That limitation is disclosed rather than hidden.
- Holdout charts use observed prior lag values. Operational multi-hour forecasts feed predictions back recursively and can accumulate more error.
- The Simulation lab demand multiplier is an explicit scenario stress applied after ML inference; it is not a retrained weather response.

## Seven-scenario comparison

Fixed start: 1 November 2026, 10:00. Horizon: 24 hours. Initial battery: 1,200 kWh at 62% SOC, except the low-battery preset. Energy values below are kWh.

| Scenario | Demand | Renewable forecast | Import | Export | Unserved | Curtailed | Current-point anomalies |
|---|---:|---:|---:|---:|---:|---:|---:|
| Normal | 8,799.24 | 4,904.71 | 4,252.71 | 259.65 | 0.00 | 0.00 | 0 |
| Low solar | 8,954.58 | 3,129.55 | 5,923.55 | 0.00 | 0.00 | 0.00 | 0 |
| Demand surge | 14,518.75 | 4,904.71 | 9,712.56 | 0.00 | 0.00 | 0.00 | 1 |
| Renewable surplus | 6,168.65 | 9,441.49 | 0.00 | 3,210.69 | 0.00 | 0.00 | 1 |
| Low battery | 8,799.24 | 4,904.71 | 3,993.06 | 0.00 | 0.00 | 0.00 | 0 |
| Grid outage | 8,799.24 | 4,904.71 | 0.00 | 0.00 | 3,659.03 | 259.65 | 0 |
| Electrical abnormality | 15,838.64 | 4,904.71 | 11,032.45 | 0.00 | 0.00 | 0.00 | 4 |

All seven returned `optimal` with solver gap 0 in this run. Maximum absolute hourly balance residual was below `3 × 10⁻¹³ kW`. The outage intentionally reports scarcity rather than violating battery or grid limits. Anomaly counts refer to the current operating point, not the entire horizon.

Normal-horizon economics under the default illustrative tariffs:

- Grid-only baseline for the same served energy: **$1,706.30**
- Optimized net cost: **$822.61**
- Estimated savings: **$883.69**
- Estimated carbon avoided: **3,482.35 kg CO₂**, using the assumed 0.71 kg/kWh factor

These are simulation calculations, not guaranteed financial or emissions outcomes.

## Issues found and corrected during validation

1. **MILP wrapper regression:** SciPy's `milp` wrapper returned a false “optimal” solution in a degenerate case, leaving load unserved while the battery had usable energy. Objective rescaling and presolve changes did not fix it. The implementation now uses the direct `highspy` HiGHS binding with SciPy sparse constraint matrices. The full backend suite passes, including carried-inventory stepping.
2. **Transformer screening:** an early horizon-wide capacity row was replaced by a separate constraint for every hour.
3. **Demand multiplier:** the multiplier is now applied explicitly to the ML demand baseline and all sectors after inference, so a 1.65× scenario genuinely raises demand by 65%.
4. **Simulation form:** derived numeric input steps rejected the default 300 kW power value in native browser validation. Power/efficiency/tariff fields now use `step="any"`; horizon remains integral.
5. **Mobile layout:** the Simulation form/preview now use min-width-safe single-column grids. The final 390 px check has no horizontal overflow.
6. **Maintenance browser test:** the completion assertion now re-queries the row after the action button disappears, and repeated test runs no longer cause strict locator ambiguity.
7. **Report carbon factor:** reports use each recorded run’s configured factor; seeded history uses the documented default.

## Non-blocking warnings and boundaries

- Backend tests emit non-fatal `datetime.utcnow()` and AnyIO deprecation warnings. They do not change the passing results.
- npm reports maintenance/deprecation notices for some transitive packages and the inactive Recharts 2 branch; the final audit reported zero known vulnerabilities.
- The application is a single-worker educational demo. It has no authentication, production rate limiting, TLS termination, schema migration framework or certified hardware-control path.
- Electrical monitoring is simulated. Risk scores are uncalibrated heuristic condition indices, not failure probabilities or remaining-useful-life estimates.
- The optimizer is a single-bus energy model with a transformer loading screen, not an AC power-flow, protection or transient-stability solver.

## Final demonstration state

After browser tests, the dirty validation database was backed up outside the deliverable and the demo database was reinitialized from the preserved synthetic datasets and trained models. The delivered demo starts in normal operation at the initial clock with one seeded inspection plan and no browser-test maintenance/upload clutter. The audit trail created by future user actions remains persistent; the in-app reset restores normal inputs and the initial clock without deleting history.
