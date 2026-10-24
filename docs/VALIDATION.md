# Verification record — 24 October 2026

## Required live inference

The original, unchanged organizer test_eval.py and sample_test_input.csv match the starter kit byte for byte. With PREDICT_ALLOW_LOCAL=0, the official evaluator returned SUCCESS for all 1,000 test rows using the published QuickML model. The standalone CSV CLI also produced exactly 1,000 finite predictions with columns timestamp,target_demand_kw and the original timestamp order.

Evidence: validation/official-self-test.txt, validation/quickml_predictions.csv and validation/live-evaluation.json, including SHA-256 hashes. Batching sends ten upstream requests for the 1,000-row relay input. No dummy or local predictions were used in these checks.

## Automated checks

36 unit/API tests pass. Coverage includes exact 160/200 kW boundaries, independent overload alerts, inclusive 18:00–22:00 hours, ordered batch inference, matching gateway project identity, CSV cleanup and missing-value imputation, battery energy/reserve/power constraints, secure public-origin handling, bounded chunked JSON, server-side session isolation, cloud-history round-trip, control-signal export and failure behavior. JavaScript syntax validation also passes.

## Public cloud and browser checks

- Public HTTPS AppSail website loads with QuickML as the default engine. The first run uses clearly identified 2015 official sample telemetry; later loads restore the browser’s saved forecast.
- Real 24-hour QuickML forecast, CSV export, 24-command JSON export, source transitions and independent overload events verified.
- A saved QuickML forecast survived a physical AppSail redeployment, verified with the same in-memory browser session before and after. See `validation/history-redeployment.txt`.
- Data Store history save/list/restore/export passed with USER scopes and server-only SELECT/INSERT permissions. A different session received HTTP 404 for the saved forecast.
- Model/research view shows the published XGB model’s cloud metrics and separately labels local chronological benchmarks.
- Scenario lab compares battery capacity against fixed demand and dispatch rules. Suggested capacity removed the sample’s modeled storage shortfall.
- At a 390×844 viewport, the page width remained 390 pixels without horizontal page overflow; charts and cards fit the mobile layout. The temporary viewport override was reset afterward.
- Deployment bundle uses universal Python wheels and imports successfully on Python 3.12; no macOS native binaries are shipped.

## Accuracy and limits

QuickML’s built-in evaluation reports RMSE 8.2733 kW, MAE 6.54336 kW and R² 0.97293. This is not a competition hidden-test score. The local 9.2494 kW chronological development RMSE uses a different evaluation split and is not a direct comparison.

Battery state and control commands are simulations; no physical switching hardware is connected. Saved history is browser-session scoped. Clearing or expiring the cookie removes access from that browser. Raw uploaded CSV files are not separately archived; parsed telemetry is retained in the durable forecast record.

## Interface refinement

The refreshed workspace adds a desktop navigation sidebar, accessible navigation icons, clearer typography and form contrast, a highlighted demand card, real 24-hour mini charts in each summary card, and a gradient demand chart. Mobile was checked at 390×844: document width 390, chart width 336, with no horizontal page overflow. Navigation and the forecast form were checked in-browser. Prediction and dispatch behavior are unchanged.

The sharp interface refinement replaces soft card corners and shadows with 3-pixel geometry, stronger dividers and higher-contrast labels. Summary spacing is tighter; forecasting and dispatch logic are unchanged.
