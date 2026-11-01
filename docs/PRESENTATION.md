# College presentation guide

## Project title
**AI-Powered Renewable Energy Optimization and Smart Grid Management System**
Application name: **HelioGrid — Energy Intelligence**

## Opening statement (about 45 seconds)

“Solar and wind generation do not naturally coincide with electricity demand. Our project connects forecasting, battery storage and grid dispatch in one intelligent system. It predicts the next 24 hours, optimizes battery and grid decisions under operating constraints, monitors simulated electrical conditions, and explains every recommendation. The application uses real trained models and a real mathematical solver, but all site measurements are clearly labeled synthetic. It is a decision-support simulation, not a certified grid controller.”

## Suggested 12-slide structure

### 1. Problem and motivation
- Renewable output varies with weather and time.
- Evening demand can peak after solar output falls.
- Uncoordinated operation wastes surplus and increases grid imports.
- Electrical stress needs monitoring, but software ML is not a protection relay.

### 2. Aim, objectives and scope
- Forecast solar, wind and sector demand.
- Optimize a battery and utility connection with explicit constraints.
- Detect simulated abnormalities and support maintenance planning.
- Provide a complete interactive web application with persistence and reports.
- Scope: single-bus educational microgrid, not a real network controller.

### 3. Integrated architecture
Show React → FastAPI → ML/optimization/monitoring → SQLite → all pages.
Emphasize that the same saved scenario and dispatch plan drives every module.

### 4. Dataset and preprocessing
- 120 days, 2,880 hourly synthetic observations.
- Physically motivated solar/wind and consumer demand profiles.
- Explicit missing-value and gross-outlier handling.
- Chronological split avoids random future-to-past leakage.
- No claim that external real-world data was used.

### 5. Machine-learning methodology
- Ridge, Random Forest and XGBoost candidates.
- Validation-based model selection and held-out test metrics.
- Weather, calendar, cyclic and lag features.
- Recursive multi-hour forecasts versus one-step holdout evaluation.
- Explain why unusually high solar R² is expected for synthetic data.

### 6. Battery model
Write:

`E[t] = E[t−1] + ηc C[t] − D[t]/ηd` for one-hour steps.

Explain SOC bounds, power limits, 90.25% default round-trip efficiency, and the binary variable preventing simultaneous charging/discharging.

### 7. Central optimization engine
- Renewable and demand balance in every hour.
- Time-of-use tariffs, degradation, curtailment and unserved-energy penalties.
- Grid import/export limits and mode exclusivity.
- Initial-energy terminal constraint avoids free end-of-horizon battery use.
- Transformer capacity screening and transparent essential-load allocation.
- SciPy sparse constraints with the HiGHS MILP solver.

### 8. Power-system monitoring
- Balanced three-phase relationships between P, Q, S, V, I and PF.
- Isolation Forest on nominal operating samples.
- Explicit voltage, frequency, power-factor and loading bands.
- Injected abnormalities are test conditions, not real faults.

### 9. Predictive maintenance and recommendations
- Condition-risk index is not a failure probability.
- Asset-specific scores are heuristic screening estimates.
- Alerts and inspection records persist.
- Acknowledgement does not change electrical conditions.
- Recommendations quote actual forecast/solver quantities.

### 10. Demonstration scenarios
Compare normal, surplus, low solar, high demand, low battery, outage and electrical abnormality. Explain outcomes rather than claiming every scenario is equally reliable.

### 11. Validation and results
- Show held-out MAE/RMSE/R² and the seasonal baseline.
- Show the executed results: 79 backend tests, 8 frontend unit tests and 7 browser integration tests passed.
- Show energy balance, SOC and mode constraints in tests.
- Demonstrate database survival across a new Python process.

### 12. Limitations and future work
Synthetic data, no AC load flow, simplified battery and risk models, no real hardware, no automatic real-data retraining. The demand multiplier is an explicit post-inference scenario stress, not a retrained model. Future: measured datasets, probabilistic forecasts, AC optimal power flow, asset-specific degradation and certified hardware integration.

## Live demonstration script (8–10 minutes)

### A. Overview — establish the system
1. Open Overview. Point out **Simulation mode** and the simulation clock.
2. Explain instantaneous kW versus horizon kWh.
3. Select a topology node. Its value comes from the current backend plan.
4. Switch generation chart between forecast and synthetic history.
5. Open Battery storage and identify inventory, usable reserve and efficiency.

### B. Models — show genuine ML
1. Open Renewable analytics → Actual vs. predicted.
2. Explain that this is the untouched synthetic holdout.
3. Open model methodology and compare candidate models.
4. State the actual metrics shown; do not describe them as real-world accuracy.

### C. Surplus and storage
1. In Simulation lab, select **Renewable surplus** and Apply & optimize.
2. Open AI optimization. Identify surplus intervals and the charge plan.
3. Open Battery storage. Show SOC staying below the maximum.
4. Return to Overview; advance one hour. Explain that inventory changed and the plan was recalculated.

### D. Outage and reliability
1. Select **Grid outage** and apply.
2. Open Smart grid. Import/export are zero.
3. If there is unserved demand, explain the battery energy/power limits and essential-first policy.
4. Emphasize that the optimizer reports scarcity instead of violating safety limits.

### E. Electrical abnormality and maintenance
1. Select **Electrical abnormality** and apply.
2. Open Power monitoring. Identify low voltage/frequency and loading/PF alerts.
3. Open Faults & maintenance. Acknowledge an event.
4. Create an inspection plan, then mark the simulated record complete.
5. Explain that administrative completion does not claim a physical repair.

### F. Data and reporting
1. Restore normal inputs and apply.
2. Open Reports & data; download the solar template.
3. Upload that template, validate and generate predictions.
4. Download predictions and a weekly energy report.
5. Show persistent table counts and explain the audit trail.

## Likely examiner questions

**Is this real-time hardware monitoring?**
No. Auto play advances a simulated clock. There is no sensor, relay or real grid connection.

**Are the ML models actually trained?**
Yes. Joblib artifacts, the registry, candidate metrics and held-out predictions are included. The API loads these models.

**Why not use LSTM?**
The small synthetic dataset does not justify it. The project implements and compares linear and tree-based models with chronological validation.

**Why can solar R² be so high?**
The target follows a known physical equation with modest noise. This is not evidence of equivalent accuracy on a real site.

**How do you prevent future data leakage?**
Chronological splitting, training-only imputation and lag features from prior observations. Multi-hour predictions feed back predicted values rather than future actuals.

**How is simultaneous charging/discharging prevented?**
A binary mode variable links each power to its permitted mode. Tests verify the product of charge and discharge power is zero.

**Where are efficiency losses represented?**
Charging adds `ηc × C`; discharging removes `D/ηd`. Both powers are AC-side values.

**Can the battery charge from the conventional grid?**
No. The renewable balance only allows renewable generation to charge the battery.

**Why might the battery stay idle despite a deficit?**
The full horizon may preserve reserve for later scarcity, or the optimizer may find grid supply cheaper than throughput/loss costs. Read the hourly explanation and constraints; do not assume every deficit must trigger discharge.

**What happens during an outage?**
Import/export limits become zero. Renewables and safe battery output serve as much demand as possible; the remainder is explicitly reported.

**Is the risk percentage a probability of failure?**
No. It is a documented heuristic condition index. There is no calibrated remaining-useful-life model or confirmed physical fault diagnosis.

**How are recommendations generated?**
From the forecast, optimizer schedule, current constraints and detector results. No random recommendation list is used.

**Does restart reset the project?**
No. SQLite stores configuration, clock, inventory and history. Models persist as files. A cross-process test checks state recovery.

## Presentation preparation checklist

- Start both services and open the overview before the presentation.
- Keep a downloaded report and the CSV template ready as a network-independent backup.
- Use the screenshots if a classroom browser cannot reach the local server.
- Reset to normal inputs after rehearsals.
- Rehearse the distinction between synthetic actuals, current predictions and historical holdout predictions.
- Never connect this demonstration directly to physical grid equipment.
