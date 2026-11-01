# HelioGrid
## AI-Powered Renewable Energy Optimization and Smart Grid Management System

A complete, integrated college-level energy intelligence application built with React, FastAPI, trained machine-learning models, SQLite, and constrained mathematical optimization.

> **Important:** This is an educational software simulation and advisory decision-support platform. Weather, generation, consumption, electrical measurements and equipment conditions are synthetic. There is no hardware connection, live weather service, real utility switching, certified protection function, or claim of real-world model accuracy.

## Quick start

Requirements: **Python 3.11–3.13**, **Node.js 20.19+ or 22.12+**, npm, and a modern browser. Verified here with Python 3.13 and Node.js 20.

From the project root:

```bash
chmod +x run.sh
./run.sh
```

The launcher installs pinned dependencies, prepares data/models/database without deleting existing state, and starts both services. Stop both with Ctrl+C.

- **Application:** http://localhost:5173
- **Interactive API documentation:** http://localhost:8000/api/docs
- **OpenAPI schema:** http://localhost:8000/api/openapi.json

The included database, synthetic datasets and trained Joblib models are ready to use. On a completely fresh checkout without models, startup trains them automatically; explicit preparation is recommended below.

### Manual installation and execution

Terminal 1 — backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python -m app.cli prepare
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Terminal 2 — frontend:

```bash
cd frontend
npm ci
npm run dev
```

Windows PowerShell backend activation: `.venv\Scripts\Activate.ps1`; set thread counts with `$env:OMP_NUM_THREADS="1"` and `$env:OPENBLAS_NUM_THREADS="1"`. The remaining backend commands are the same. Start the frontend in a second terminal.

Vite proxies browser `/api` requests to FastAPI on port 8000. Browser code never calls a sandbox-local address. Both servers bind to `0.0.0.0` for hosted previews. The development server permits the preview host; this permissive development setup is not a production access-control policy.

### Single-port production-style preview

```bash
cd frontend
npm ci
npm run build
cd ../backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. FastAPI serves the built React app and API together. Rebuild after frontend changes. This is a local demonstration deployment, not a hardened public hosting configuration.

## Abstract

Renewable generation and electricity demand vary over time. Without coordination, surplus generation can be wasted while expensive grid electricity is purchased at other hours. HelioGrid combines solar, wind and demand forecasting with an efficiency-aware battery model, constrained energy dispatch, electrical condition monitoring, and explainable recommendations. A common backend and persistent database connect every module. Users can explore normal operation, renewable scarcity and surplus, demand surges, reserve depletion, grid outages and abnormal electrical conditions.

## Problem statement

Design and implement a unified simulation that:

1. Predicts solar generation, wind generation and electricity demand.
2. Stores surplus renewable energy within physical battery limits.
3. Minimizes procurement cost, curtailment and unmet demand.
4. Monitors simulated electrical conditions and identifies abnormal patterns.
5. Provides traceable recommendations and maintenance screening.
6. Persists history and lets users evaluate scenarios and compatible CSV data.

## Aim and objectives

- Increase renewable utilization and reduce avoidable grid dependence.
- Represent charging/discharging efficiencies and SOC constraints correctly.
- Use actual trained models and a real solver rather than static dashboard numbers.
- Explain decisions from calculated forecasts, inventories, constraints and tariffs.
- Distinguish measurements, predictions, synthetic actuals and heuristic risk estimates.
- Offer a reproducible, testable platform suitable for a final-year project demonstration.

## Scope

The simulated microgrid contains a 650 kW solar plant, 450 kW wind plant, 1,200 kWh battery, residential/commercial/industrial consumers and a utility connection. It uses a **single-bus energy balance**, not a multi-bus AC load-flow model. Default battery power is 300 kW in either direction, with 15–95% SOC and 95% efficiency per direction. Defaults are editable in Simulation lab.

The application does not switch real loads, operate protection relays, diagnose confirmed physical failures, or guarantee financial savings.

## Included application pages

| Page | Functionality |
|---|---|
| Overview | Current forecast operating point, SOC, carbon estimate, historical/forecast charts, interactive topology, health and calculated recommendations |
| Renewable analytics | Solar/wind forecasts, historical generation, hourly/daily totals, weather, holdout actual vs. predicted, model comparison and EDA |
| Load forecasting | Current/peak/horizon demand, sector mix, hourly consumer demand, daily totals and supply-risk warnings |
| Battery storage | SOC, usable reserve, configuration, efficiency, protections, inventory/charging schedule and explanations |
| Smart grid | Selectable generation/storage/load/grid nodes, backend-driven animated flows, sector allocation and hourly distribution |
| Power monitoring | V, I, Hz, P, Q, S, PF and transformer loading; trends, rules, Isolation Forest and a non-persistent electrical test |
| Faults & maintenance | Asset condition scores, heuristic risk, abnormal-event history, acknowledgement, inspection creation and completion |
| AI optimization | Solver status/gap, objective, constraints, cost comparison, calculated suggestions and explainable dispatch |
| Simulation lab | Seven scenarios, weather/demand overrides, battery and market settings, grid availability/export, apply and clock controls |
| Reports & data | Latest-day/7-day/30-day CSV reports, database inventory, validated CSV batch prediction and downloadable templates/results |

Dark/light themes, responsive navigation, loading/error states, downloadable CSVs and interactive charts are implemented. Topology uses selectable SVG/React nodes rather than React Flow; this is the permitted suitable alternative.

## Architecture

```text
React + Vite + Tailwind + Recharts + Lucide + React Router
                         │ relative /api requests
                         ▼
                 FastAPI + Pydantic
                         │
       ┌─────────────────┼──────────────────┐
       ▼                 ▼                  ▼
 ML pipelines      optimization       simulation/monitoring
 sklearn/XGBoost    SciPy + HiGHS     physics + Isolation Forest
       │                 │                  │
       └─────────────────┼──────────────────┘
                         ▼
             SQLAlchemy + SQLite (WAL)
                         │
              historical records/reports
```

Every run stores its input configuration, forecast, optimization decisions, operating state, anomalies and equipment estimates. Applying inputs recalculates the plan. Advancing the clock realizes a simulated hour, carries battery inventory forward, and re-optimizes. Recommendations do not exist independently of this pipeline.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for equations, variable definitions, assumptions and the decision loop.

## Technology stack

- Frontend: React 18, Vite 6, Tailwind CSS 3, Recharts 2, Lucide React, React Router 7.
- Backend: Python, FastAPI, Pydantic 2, SQLAlchemy 2, Uvicorn.
- ML/data: Pandas, NumPy, Scikit-learn, XGBoost CPU, Joblib, SciPy.
- Database: persistent SQLite with WAL and foreign keys.
- Validation: Pytest, FastAPI TestClient, Vitest, Testing Library and Playwright.

Dependency versions are pinned in `backend/requirements.txt`; npm transitive versions are locked in `frontend/package-lock.json`. Compatible security updates were applied during implementation. XGBoost uses the CPU wheel to avoid unnecessary CUDA dependencies.

## Dataset description and provenance

**No external dataset is represented as having been downloaded.** The permitted synthetic-data alternative is used so the complete project runs without credentials or incompatible data alignment.

- Generator: `backend/app/simulation/generator.py`.
- Raw data: `backend/data/synthetic_raw.csv`.
- Cleaned data: `backend/data/synthetic_clean.csv`.
- Holdout predictions: `backend/data/holdout_predictions.csv`.
- EDA: `backend/data/eda.json`.
- Model report: `backend/trained_models/registry.json`.

The default dataset contains **2,880 hourly rows over 120 days**, ending before the simulation start. It is Indore-inspired, not measured Indore data. Seeded random generators make it reproducible. Solar follows irradiance and cell-temperature derating; wind follows a cut-in/rated/cut-out curve with air-density adjustment. Demand combines morning/evening residential peaks, weekday commercial activity, industrial baseload and cooling demand. The raw data intentionally contains missing readings and gross sensor spikes.

Potential future real-data sources include NREL, Kaggle and Open Power System Data. They are **not used or claimed as sources in this build**. Real data would require site-specific capacity normalization, units, timezone alignment, weather-feature compatibility and new validation.

## Machine-learning methodology

1. Validate and clean raw weather/target data using explicit physical bounds.
2. Convert invalid observations to missing; interpolate short interior gaps.
3. Fit remaining feature imputation on training data only.
4. Engineer hour/month/season, cyclical time, weekend, cooling-degree, wind-cube and lag features.
5. Split chronologically: 70% training, 15% validation, 15% held-out testing.
6. Compare Ridge, two Random Forest specifications and two XGBoost specifications.
7. Select by validation MAE; refit on train + validation; evaluate the saved model on the holdout.
8. Persist models and feature schemas with Joblib.
9. Serve predictions through APIs and use recursive lag predictions in the optimizer. An explicit what-if demand multiplier then scales the ML baseline and all consumer sectors equally; the fitted model itself is not retrained for each scenario.
10. Train Isolation Forest on nominal synthetic electrical operating samples.

LSTM is intentionally omitted: this small synthetic dataset does not justify a deep sequence model, and the requested tree/linear methods are implemented and genuinely trained. Hyperparameter search is a transparent discrete comparison rather than an expensive exhaustive search.

### Included trained-model results

These are results on the included synthetic holdout, **not real-world accuracy**. Exact values and all candidate comparisons are available in the registry and UI.

| Task | Selected model | MAE | RMSE | R² |
|---|---|---:|---:|---:|
| Solar | XGBoost, depth 3 | 2.82 kW | 6.90 kW | 0.9981 |
| Wind | Random Forest, depth 14 | 6.05 kW | 8.14 kW | 0.9845 |
| Demand | Random Forest, depth 14 | 7.32 kW | 19.85 kW | 0.8892 |

High solar accuracy is expected because the target is generated from a documented physical relationship plus noise. Holdout charts use observed prior lag values; long-horizon operation feeds predictions back recursively and can accumulate more error.

Retrain explicitly:

```bash
cd backend
source .venv/bin/activate
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m app.cli train
```

Retraining replaces model artifacts and data reports, not the historical SQLite audit trail. Historical predictions remain labeled with their stored model version. Restart the backend after retraining to clear its model cache. For a rigorous new-model experiment, use a separate data/model/database directory.

## Battery and optimization mathematics

Battery energy update:

```text
E[t] = E[t−1] + η_charge × charge[t] × Δt
                  − discharge[t] × Δt / η_discharge
```

The MILP enforces minimum/maximum energy, charging/discharging power, binary mode exclusivity, renewable balance, demand balance, import/export limits and a conservative transformer loading screen. It cannot simultaneously charge/discharge or import/export. It cannot charge the battery from the conventional grid.

The objective combines time-of-use import cost, throughput degradation, curtailment and unserved-load penalties, minus export revenue. Curtailment and grid-dependency penalties favor productive renewable use. When the grid is available, terminal energy must be at least initial energy; an outage may consume initial stored energy down to the safe minimum. This prevents end-of-horizon free-energy artifacts.

Essential-load fractions are transparent policy assumptions. Under scarcity, essential demand is allocated first, followed by flexible demand. Unserved energy is reported, never hidden by relaxing safety constraints.

The implementation uses HiGHS MILP (direct `highspy` binding with SciPy sparse constraints). See the architecture document for the complete formulation and solver settings.

## Power monitoring and predictive maintenance

A balanced three-phase simulation computes apparent/reactive power, current and transformer loading from served active power, voltage and power factor. Isolation Forest identifies unusual multivariate patterns. Explicit operating bands detect voltage/frequency deviations, low PF and excessive transformer loading.

Asset failure-risk is a **heuristic 0–100 condition index**, not a calibrated probability or confirmed failure forecast. It combines operating stress, normalized ML abnormality and recent event frequency. Non-transformer assets use documented scaling, not independently trained physical degradation models. Completing an inspection records an administrative action; it does not fabricate an improvement in sensor readings.

**Software alerts do not replace protection relays, interlocks, certified controls or qualified electrical personnel.**

## Database design

The thirteen persistent tables are:

1. `renewable_generation`
2. `electricity_consumption`
3. `weather`
4. `power_measurements`
5. `battery_status`
6. `ml_predictions`
7. `optimization_results`
8. `grid_conditions`
9. `anomalies`
10. `equipment_health`
11. `maintenance_records`
12. `user_configuration`
13. `simulation_history`

Default file: `backend/data/heliogrid.db`. Configuration holds the current scenario, clock, battery inventory and latest run ID. Actual/simulated history is unique by timestamp; forecast revisions and runs are stored separately. Initialization seeds 35 days of synthetic history only when the history is empty. Restarting does not reset the clock or battery.

There is no automatic schema migration framework in this initial release. Back up the database before changing schemas; a future production version should add Alembic migrations.

## API summary

Interactive request/response schemas are at `/api/docs`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service/model readiness and simulation notice |
| GET | `/api/dashboard` | Integrated state, forecast, optimization, monitoring, recommendations and history |
| GET | `/api/forecast` | Hourly forecast, horizon totals and model registry |
| POST | `/api/predict/{solar|wind|load}` | Compatible-record batch predictions |
| GET | `/api/models`, `/api/eda`, `/api/evaluation` | Metrics, EDA and held-out actual/predicted data |
| GET | `/api/battery` | Configuration, inventory and schedule |
| POST | `/api/optimization` | Apply configuration and solve a new dispatch plan |
| GET | `/api/grid` | Current flows and hourly distribution |
| GET | `/api/monitoring` | Electrical measurements/trends and current detector result |
| POST | `/api/monitoring/test` | Test detector on query parameters without changing grid state |
| GET | `/api/anomalies` | Historical abnormal events |
| POST | `/api/anomalies/{id}/acknowledge` | Persist review note |
| GET | `/api/equipment` | Current health/risk estimates |
| GET/POST | `/api/maintenance` | List/create inspection records |
| PATCH | `/api/maintenance/{id}` | Mark simulated inspection complete |
| GET | `/api/simulation/state`, `/api/simulation/scenarios` | Current state and scenario catalog |
| POST | `/api/simulation` | Apply a scenario/configuration |
| POST | `/api/simulation/step` | Realize 1–24 simulated hours and re-optimize |
| POST | `/api/simulation/reset` | Restore normal inputs and the initial clock without deleting history |
| GET | `/api/history/{kind}` | Generation, consumption, weather, power, battery, predictions, optimization, grid, runs or equipment |
| POST | `/api/upload` | Multipart CSV validation and inference |
| GET | `/api/upload/template?target=solar` | Compatible 48-hour input template |
| GET | `/api/reports?period=weekly&format=csv` | Daily/weekly/monthly JSON or CSV report |
| GET | `/api/database/summary` | Table counts and persistence information |

Example:

```bash
curl -X POST http://localhost:8000/api/simulation \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"outage","horizon":24}'

curl -X POST http://localhost:8000/api/simulation/step \
  -H 'Content-Type: application/json' -d '{"hours":1}'

curl 'http://localhost:8000/api/reports?period=weekly&format=csv' -o report.csv
```

Named scenario presets intentionally set their defining inputs. For arbitrary combinations, use `scenario: "normal"` with explicit overrides. The UI switches to custom/normal inputs when a preset is edited.

## CSV upload

Maximum 2 MB, 5,000 rows, 60 columns; consecutive hourly timestamps without duplicates. Required columns:

- All tasks: `timestamp`.
- Solar: `irradiance` (W/m²), `temperature` (°C), `humidity` (%), `cloud_cover` (%), `wind_speed` (m/s).
- Wind: `wind_speed`, `wind_direction` (degrees), `temperature`, `air_density` (kg/m³).
- Load: `temperature`, `humidity`, `cloud_cover`.
- Optional actual targets for evaluation: `solar_kw`, `wind_kw`, `total_kw`.

Use the downloadable template. Include 24–48 preceding hours where possible: one-hour and 24-hour lag features materially affect predictions. If a complete lag history is absent, documented zero fallbacks are used; this can reduce accuracy. Weather values must satisfy the supported physical ranges. Blank optional actuals are allowed; invalid actual values are rejected. Predictions are stored in SQLite and downloadable as CSV. Uploading does not automatically retrain the models.

## Reports, costs and carbon

- Hourly kW is integrated over one hour to obtain kWh.
- Daily reports cover the latest simulated calendar day, which may be partial; weekly/monthly reports cover the latest seven/thirty calendar days represented in history.
- Synthetic realized history and explicitly marked forecast operating points coexist; forecast revisions are not double counted.
- Optimization savings compare the **same served energy** against grid-only procurement, include battery throughput cost and subtract export revenue, and exclude unserved load from the baseline.
- Carbon avoided is an estimate based on utilized renewable energy and an assumed emissions factor. Reports use each recorded run’s configured factor; seeded history defaults to 0.71 kg CO₂/kWh. Neither is a certified carbon accounting calculation.
- Tariffs are illustrative USD values. Peak hours are 17:00–22:00 at 1.5× base; overnight 00:00–06:00 is 0.8× base.

## Testing and validation

Backend tests use an isolated temporary database and freshly trained models; they do not alter the running demonstration database.

```bash
cd backend
source .venv/bin/activate
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m pytest tests -q
```

Frontend unit tests and production build:

```bash
cd frontend
npm ci
npm test
npm run build
npm audit
```

Browser integration tests, with both application servers running:

```bash
cd frontend
npx playwright install --with-deps chromium
npm run test:e2e
```

Tests cover model persistence/prediction, preprocessing, physical generation, demand forecasts, battery charge/discharge/efficiency/bounds, invalid operations, surplus/deficit, essential allocation, electrical consistency, all scenario constraints, abnormal electrical detection, API validation, upload errors, reports, maintenance, acknowledgement, clock progression, database persistence across sessions and a separate Python process, and frontend rendering/interactions.

See [docs/VALIDATION.md](docs/VALIDATION.md) for the executed verification record: **79 backend tests, 8 frontend unit tests and 7 browser integration tests passed**; production build and npm audit also passed. Raw logs are in `docs/validation/`, the seven-scenario comparison is `docs/scenario-validation.json`, and browser screenshots are in `docs/screenshots/`.

## College presentation

A detailed 12-slide narrative, live demonstration sequence and likely examiner questions are provided in [docs/PRESENTATION.md](docs/PRESENTATION.md).

Recommended demonstration:

1. Show the integrated overview and explain units and synthetic-data labeling.
2. Open model metrics and actual-vs-predicted holdout results.
3. Apply renewable surplus and inspect the optimized battery charging plan.
4. Advance one hour and show inventory persistence.
5. Apply a grid outage and discuss unserved energy and essential loads.
6. Apply abnormal electrical conditions, acknowledge an alert and plan an inspection.
7. Upload the provided CSV template and download predictions.
8. Download a weekly report and explain cost/carbon assumptions.

## Security and reliability

Pydantic validates numeric ranges and battery SOC ordering. CSV size/schema/value checks reject invalid uploads. SQLite transactions, WAL and foreign keys preserve consistent records. State transitions are serialized within the single backend worker. Missing models/history produce explicit errors or initialization, not fabricated API success. Frontend requests have timeouts, retry states and an error boundary. No secrets are embedded; optional environment overrides are documented in `backend/.env.example`.

This local educational build has no user authentication, role-based access, TLS termination, production rate limiting or hardware-control interface. Do not expose it directly as a public operational service. Add authentication, migrations, HTTPS, observability, backups and a multi-user concurrency design before any production adaptation.

## Limitations

- Synthetic, single-site data; no external measured-data validation.
- Single-bus active-energy model; no three-phase unbalance, harmonics, short-circuit, transient stability or network load-flow solution.
- Weather overrides are constant over the horizon; no live numerical weather prediction.
- One aggregate battery; no cell-level thermal/electrochemical model or measured degradation.
- Flexible-load shifting is an explained recommendation, not an independently optimized appliance schedule.
- Equipment risk is heuristic screening, not calibrated remaining-useful-life prediction.
- Model retraining from arbitrary uploaded data is not automatic.
- Forecast uncertainty/scenario trees and multi-objective Pareto optimization are future work.
- SQLite/local locks are appropriate for the demonstration, not concurrent multi-operator control.

## Future enhancements

Validated local datasets; probabilistic forecasts; AC optimal power flow; weather API integration; stochastic/robust optimization; flexible-load scheduling; asset-specific degradation models; Alembic migrations; authentication/RBAC; PostgreSQL; container deployment; hardware-in-the-loop testing through a certified gateway; and independent electrical-safety review.

## Project layout

```text
renewable-smart-grid/
├── frontend/
│   ├── src/{components,pages,charts,services,hooks,assets}/
│   ├── e2e/
│   ├── package.json / package-lock.json
│   └── vite.config.js / tailwind.config.js
├── backend/
│   ├── app/{routes,services,models,schemas,database,ml,optimization,simulation,utils}/
│   ├── data/                  # synthetic datasets + persistent SQLite
│   ├── trained_models/        # saved models + registry
│   ├── tests/
│   └── requirements.txt
├── docs/                      # architecture, presentation, validation, screenshots
├── run.sh
└── README.md
```
