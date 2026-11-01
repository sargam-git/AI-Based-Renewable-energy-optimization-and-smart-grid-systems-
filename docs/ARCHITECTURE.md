# HelioGrid architecture and mathematical model

## 1. One integrated decision loop

```text
Synthetic weather / user scenario
               │
               ▼
Solar, wind and demand models ───────► hourly forecast table
               │                              │
               ▼                              ▼
         SQLite history             SciPy + HiGHS MILP optimizer
               │                     │    │    │    │
               ▼                     ▼    ▼    ▼    ▼
       Electrical simulation       battery grid export curtailment
               │                     │       │
               ▼                     ▼       ▼
       Isolation Forest + rules     shared dispatch plan
               │                     │       │
               ▼                     ▼       ▼
       Anomalies / risk         explanations / recommendations
               │                     │
               └──────────┬──────────┘
                          ▼
                React control-center pages
                          │
              apply scenario / advance clock
                          │
                          ▼
             Persist run and update battery state
```

The simulation clock is deliberately independent of wall time. The initial clock is 1 November 2026, 10:00 in the educational site's local time. Weather and demand use a fixed Indian standard-time convention (UTC+05:30, no DST). Audit creation timestamps are UTC. Auto play realizes one hour every 12 seconds; it does not imply hardware telemetry.

## 2. Units and plant assumptions

| Quantity | Convention |
|---|---|
| Solar / wind / demand / dispatch | kW, AC side |
| Time step | 1 hour |
| Energy | kWh = kW × 1 h |
| Battery inventory | kWh |
| Voltage | V, three-phase line-to-line RMS |
| Current | A per line |
| Active / reactive / apparent power | kW / kVAr / kVA |
| Tariff and degradation cost | illustrative USD/kWh |
| Carbon intensity | configurable assumed kg CO₂/kWh; default 0.71 |

Solar: 650 kW. Wind: 450 kW. Battery: 1,200 kWh, 300 kW charge/discharge, 15–95% SOC, 95% efficiency in each direction. Transformer: 1,000 kVA. Grid: 800 kW import and 400 kW export. These are editable assumptions where exposed in the simulation UI, not nameplate data from a real site.

## 3. Forecasting and leakage control

The deterministic generator provides 120 days (2,880 hourly observations), ending immediately before the initial simulation clock. It includes seasonal and diurnal weather, weekday commercial demand, cooling demand, generation noise, missing sensor readings and gross sensor spikes.

Raw and cleaned CSVs are stored separately. Gross physical-bound violations are converted to missing values. Interior gaps of up to two hours are interpolated. Remaining feature gaps use a median imputer fitted inside each model pipeline. Target gaps are excluded from fitting. Calendar, cyclic, wind-cube, cooling-degree, previous-hour, previous-day and rolling-load features are generated.

A chronological 70/15/15 train/validation/test split is used. Ridge, two Random Forest specifications and two XGBoost specifications are fitted. Validation MAE selects the specification; it is refitted on train + validation and evaluated on the untouched final test period. All selected models and the model registry are saved with Joblib. MAE, RMSE, R² and a 24-hour seasonal baseline are reported.

Holdout actual-vs-predicted charts use one preceding observed value for lag features. Multi-hour simulation forecasts feed their own predictions back recursively, so they do not consult future actual targets. These two evaluation modes are not identical; recursive errors can accumulate.

### Scenario demand stress

The demand model forecasts the normal operating profile. The Simulation lab multiplier is applied **after inference** to the predicted total and each consumer sector. Thus 1.65× means 65% higher demand than the same ML baseline, rather than asking a model trained on normal demand to infer an unseen multiplicative intervention. Solar/wind overrides change weather inputs to the fitted renewable models.

## 4. Battery equations

Let E[t] be energy at the end of hour t, C[t] the AC charging power, D[t] the AC discharging power, and Δt = 1 h:

```text
E[t] = E[t−1] + ηc C[t] Δt − D[t] Δt / ηd
Emin ≤ E[t] ≤ Emax
0 ≤ C[t] ≤ Pcharge_max · z[t]
0 ≤ D[t] ≤ Pdischarge_max · (1 − z[t])
z[t] ∈ {0,1}
SOC[t] = 100 E[t] / capacity
```

The binary variable z prevents simultaneous charging and discharging. No constraint permits charging from the utility grid. Round-trip efficiency is ηc × ηd. Applying a scenario explicitly resets initial energy; advancing the clock carries inventory forward.

## 5. Optimizer

For each hour, ten variables represent direct renewable supply, charging, discharging, import, export, curtailment, unserved demand, end-of-hour inventory, charge mode and import mode.

```text
R[t] = direct[t] + C[t] + export[t] + curtail[t]
demand[t] = direct[t] + D[t] + import[t] + unserved[t]
served[t] = direct[t] + D[t] + import[t]
```

The objective minimizes:

```text
Σ (tariff[t] + 0.001) import[t]
+ Σ degradation_cost (C[t] + D[t])
+ Σ 0.035 curtail[t]
+ Σ 100 unserved[t]
− Σ export_tariff export[t]

```

The unserved-energy penalty is a planning penalty, not an actual electricity tariff. It is excluded from displayed net procurement cost.

Import and export use another binary mode. Disabled grid connections have zero limits. With the grid available, final energy must be at least initial energy, preventing the optimizer from treating initial inventory as free energy. During an outage, it may use that inventory down to the safety floor. A 950 kW load-serving capacity screen approximates 95% transformer loading at 0.95 power factor. This is not an AC power-flow or protection model.

Residential, commercial and industrial essential fractions are 65%, 35% and 25%. Under scarcity, essential requests are served proportionally first; remaining supply serves flexible requests proportionally. Sector requests are scaled to the independently forecast total before allocation. This is a transparent policy allocation, not independently optimized appliance control.

The solver is the direct HiGHS MILP binding (`highspy`) with SciPy sparse matrices, a 25-second limit and relative gap target 0.000001. A failed solve returns an error rather than silently fabricating a plan. Explanations and recommendations are constructed from the solved values.

## 6. Realizing a simulated hour

A step takes the first optimized interval, generates the corresponding synthetic weather and demand, limits charging to realized surplus, applies battery efficiency and power constraints, then adjusts grid import/export and unserved demand. It stores the realization, advances the clock and re-optimizes. Historical actuals are unique by timestamp; forecast revisions and scenario runs are retained separately and are not summed as repeated consumption.

## 7. Electrical monitoring and risk

The balanced three-phase relationships are:

```text
S = P / PF
I = 1000 S / (√3 V_LL)
Q = √(S² − P²)
transformer loading = 100 S / transformer_kVA
```

An Isolation Forest is trained on nominal synthetic voltage, current, frequency, power factor and transformer loading. Explicit bands catch voltage outside ±5%, frequency outside 49.7–50.3 Hz, transformer warning above 85%, critical loading above 100%, and power factor below 0.9. Scenario electrical disturbances are intentionally injected test conditions; they are not derived from a transient stability or short-circuit solver.

Risk index = 100 × (0.50 operating stress + 0.32 normalized ML abnormality + 0.18 recent-event frequency). Recent events are distinct prior timestamp/parameter pairs, capped at five. Feeder, solar and wind asset indices are heuristic scalings of the bus index, not separately trained failure models. These scores are not calibrated probabilities and never confirm a physical fault. Maintenance completion records an administrative action; it does not magically reset measured risk.

## 8. Persistence and boundaries

SQLite WAL mode and foreign keys are enabled. SQLAlchemy maps thirteen domain tables. Configuration and current battery inventory are committed with each run. A fresh process reads the same database; tests verify cross-process persistence. Models are files, while metrics and every prediction/decision reference the application data model.

This is a single-user, single-worker educational service. A process-local lock serializes simulation state changes. It is not a multi-operator SCADA system, authenticated production API, hardware gateway, protection relay, or distributed transaction system.
