# Catalyst deployment record

GridLens has a separate Catalyst project in the Neev organization, India data center.

- Organization: `60093095288`
- Project: `92358000000016001`
- Environment: Development
- Public website: https://gridlens-50047133296.development.catalystappsail.in
- Hosting: AppSail `gridlens`, Python 3.12, 256 MB
- AppSail ID: `92358000000016025`
- Dataset: `GridLens_Hourly_Demand`, 4,000 rows, 67 columns including the target
- Pipeline: `GridLens Demand Regression`
- Published model: `GridLens Hourly Demand`, XGB Regression, version V1
- Endpoint: `GridLens Demand API`

QuickML's built-in evaluation reports RMSE 8.2733 kW, MAE 6.54336 kW and R² 0.97293. These are AutoML evaluation metrics, not a hidden-test score or the local model's chronological holdout result. Machine-readable provenance is in `models/quickml-evaluation.json`.

The hosted website initializes request-scoped AppSail authentication through Zoho's official Python SDK and sends validated multi-row inference requests to the published QuickML API. Its endpoint key lives in Catalyst runtime settings; it is excluded from source archives. The standalone `predict.py` calls the hosted `/api/predict` relay by default, and can alternatively use separately authorized OAuth credentials. Never copy connector or CLI tokens into application configuration.

A complete live 24-row forecast was verified through the public HTTPS API and browser. The tested sample returned peak demand 267.37 kW at 18:00, 16 storage-dispatch hours and 15 critical-overload hours. These are sample forecasts, not observed loads.

Deployment was completed through Catalyst's console. The local CLI device login did not complete; do not treat the CLI as authenticated. `app-config.json` is a template and does not include the live secret. If switching to a linked CLI deployment, preserve all live runtime settings securely before redeploying, since CLI configuration can replace console-only values.

The app accepts its exact configured `GRIDLENS_PUBLIC_ORIGIN` for same-origin browser requests behind the Catalyst proxy, and bounded terminated WSGI streams for chunked JSON requests. Hosted run history is stored durably in Catalyst Data Store table `GridLensRuns` (`92358000000019001`). Both roles have USER scope; App Administrator has SELECT/INSERT only, and App User has no table permissions. The backend checks a hashed browser-session key for all history reads. SQLite is used only for unconfigured local development.

The deployed `QUICKML_REQUEST_MODE=batch` was verified with multi-row predictions. The original `test_eval.py` returned SUCCESS for 1,000 real QuickML predictions, and the full CSV CLI independently passed row count, finiteness, column names and timestamp order. Validation artifacts include the original self-test output and the complete prediction CSV.
