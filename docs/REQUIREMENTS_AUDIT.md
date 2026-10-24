# HackSphere 3.0 requirement audit

Audited against the supplied PROBLEM_STATEMENT.pdf and the matching original starter-kit PROBLEM_STATEMENT.md on 24 October 2026. The original evaluator and sample test input are unchanged.

| Required item | Implementation | Verification |
| --- | --- | --- |
| Train and publish a regression model inside QuickML | Published GridLens Hourly Demand, XGB Regression, V1; 4,000 labeled training rows | Real endpoint predictions; QuickML evaluation metadata in models/quickml-evaluation.json |
| Form or CSV telemetry ingestion | CSV upload, drag/drop, paste and a 24-hour editable form | Browser workflow and API validation tests |
| Clean data and handle missing weather values | Schema/unit/range checks, finite numbers, training-median imputation | Telemetry tests, including DataFrame NaN and malformed CSV |
| Consistent training/inference feature vectors | Shared advanced_features transformation and data/quickml_training.csv; no target or future demand supplied as input | Published model accepted every one of the 1,000 supplied test rows |
| 24 hourly QuickML forecasts | Live default engine; a complete 24-hour request to the published endpoint | Public HTTPS/API and browser checks |
| Storage when demand >160 OR hour 18–22 inclusive | Server-side dispatch_mode and build_dispatch | Exact boundary tests at 160, just above 160, 17:00, 18:00, 22:00 and 23:00 |
| Main grid otherwise | Same server-side controller | Complement and time-boundary tests |
| Independent critical overload at demand >=200 | Critical flag is evaluated separately from grid mode | Exact 200 boundary tests and exported signal tests |
| Automated transition signals | Per-hour source commands, transition/overload/shortfall event log, JSON export | 24-command live export, independent alert assertions |
| Demand curves, active state, SOC, overload alerts | Interactive demand/SOC charts, selected-hour source diagram, schedule and alerts | Public browser checks and 390-pixel mobile layout check |
| Public Catalyst Slate/AppSail app | Frontend and backend on public AppSail HTTPS URL | https://gridlens-50047133296.development.catalystappsail.in |
| predict(input_df) returns one number per row in order | Deployed QuickML relay, at most 100 rows per batch; direct OAuth also supported | Original test_eval.py returned SUCCESS for 1,000 real predictions |
| CSV CLI with timestamp,target_demand_kw | predict.py --input ... --output ... | 1,000 real CLI rows, exact headers, finite values and preserved timestamps |
| Mandatory original self-test | Original organizer file, byte-identical | validation/official-self-test.txt and hashes in validation/live-evaluation.json |
| Full source ZIP or public repository | GridLens_Submission.zip | Source package inspection; frontend/backend, scripts, data and documentation included |
| README with setup, architecture and environment variables | README.md plus linked Catalyst/QuickML guides and .env.example | Package inspection; no secret credentials in source |

## Improvements beyond the minimum

- Durable Catalyst Data Store history, with USER scopes, server-only SELECT/INSERT operations and hashed browser-session ownership checks.
- Battery scenario lab, power/reserve/efficiency constraints and minimum feasible capacity estimates.
- Published QuickML model metrics displayed separately from the local chronological benchmark.
- Batched cloud inference; a 1,000-row relay run uses ten upstream requests.
- Research references, telemetry-range diagnostics, CSV and machine-readable control-signal downloads.

## Recommended architecture versus required deliverables

The brief labels its service table as a recommended architecture and explicitly permits AppSail for the public application URL. This app serves frontend and backend together on AppSail and persists parsed telemetry/forecast records in Data Store. Separate Slate hosting and raw-file retention in Stratus are optional choices and are not claimed to be implemented.

## Limits that remain explicit

The hidden test dataset is unavailable, so no hidden-test accuracy or winning rank is claimed. QuickML built-in RMSE is 8.2733 kW; it uses a different evaluation split from the local benchmark. Battery state and controller commands are simulations with no physical hardware connected. History is browser-session scoped: clearing or expiring the cookie removes that browser’s access. Raw uploaded files are not archived separately. Account usage limits and service availability apply.

The app and code are ready for submission. The organizer’s form has not been submitted; team/participant details and the final submission remain with the participant. Deadline: 28 October 2026, with no exact cutoff supplied in the email.
