# Research review and engineering decisions

Reviewed 24 October 2026. Sources below are original research, author material, project repositories, or official documentation. Their methods informed the design; their published accuracy claims do not establish this project's accuracy. No project code or imagery was copied from these references.

| Source | Relevant idea | GridLens implementation | Boundary |
| --- | --- | --- | --- |
| Ben Taieb & Hyndman, 2014: [A gradient boosting approach to the Kaggle load forecasting competition](https://otext.robjhyndman.com/publications/kaggleloadforecasting/) | Weather/calendar structure and comparison with boosting for hourly demand | Compare weather/time regression, richer hour interactions, gradient boosting, and a residual hybrid | This starter has no demand history at inference. We do not create unavailable demand lags or claim to reproduce the competition experiment. |
| Hyndman & Athanasopoulos: [Time series cross-validation](https://otexts.com/fpp3/tscv.html) | Rolling origins train only on observations earlier than their validation period | Two chronological folds; a separate later development segment; explicit dates/counts | Only 4,000 labeled rows and two folds are available. Development error is not a hidden-test estimate. |
| Angelopoulos & Bates, 2021/2022: [A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification](https://arxiv.org/abs/2107.07511) | Forecast uncertainty should be made explicit, with assumptions visible | A finite-sample residual-quantile reference band, empirical coverage measurement, and threshold-watch warnings | We do not claim conformal validity: serial dependence, calibration transfer to a refitted model, and seasonal shifts violate the conditions needed for a simple coverage guarantee. |
| Henri et al., 2020: [pymgrid paper](https://arxiv.org/abs/2011.08004) and [project](https://github.com/Total-RD/pymgrid) | Separate components and explicit energy balancing, battery energy/power bounds, reproducible simulation | Battery reserve, efficiency, power-limit and energy-limit diagnostics, shortfall accounting, reproducible scenarios | We do not run pymgrid or claim reinforcement-learning control. The repository indicates newer development has moved to python-microgrid. |
| PyPSA: [Rolling-horizon optimization example](https://docs.pypsa.org/stable/examples/rolling-horizon/) | Finite-horizon storage planning and the effect of limited forecasts | A battery what-if workbench and feasibility capacity search over the fixed forecast | No market price inputs were supplied; this is a feasibility simulation, not an economic optimum or a PyPSA optimization. |
| scikit-learn: [GradientBoostingRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingRegressor.html) | Reproducible regression candidates and a defined tree prediction interface | Optional training dependency; portable JSON evaluation checked against the training estimator | The web server itself keeps standard-library inference and has no scientific dependency requirement. |

## Measured comparison

All methods use only the supplied training labels and weather/time inputs. Richer features include hour indicators, hour-specific cooling responses, heating/cooling terms, solar/temperature interaction, hour harmonics, and weekend information. No holiday locale is invented from timezone-unspecified timestamps.

| Candidate | Rolling-origin RMSE (kW) |
| --- | ---: |
| Original ridge baseline | 12.2941 |
| Weather + hourly interactions | 10.3940 |
| Gradient boosted trees | 10.1641 |
| Weather/calendar + residual boosting | 10.4577 |

The one-standard-error simplicity policy chooses weather + hourly interactions. The small CV difference from boosted trees does not justify the more complex model under this policy. The two folds have substantial variation; this is not a definitive model ranking across all seasons.

On the same later 800-row development segment used in the initial project, the selected model scores **9.2494 kW RMSE**, versus **11.7753 kW** for the original ridge, a **21.45% reduction**. MAE is **7.4241 kW**. Results are retrospective development comparisons: this segment has been inspected during development, and no preregistered or external untouched-test claim is made. Hidden-test accuracy remains unknown. The published QuickML model now has a separate built-in evaluation recorded in [models/quickml-evaluation.json](../models/quickml-evaluation.json).

## Uncertainty implementation

The selected model fit on the first 2,800 observations generates absolute residuals for the following 400 observations. The finite-sample 90% reference quantile uses rank `ceil((n+1)*0.9)`, clipped to the available calibration size. The resulting reference radius is **17.3449 kW**.

A point model fit on the first 3,200 rows is evaluated on the later 800 rows using that reference radius; measured coverage is **94.62%**. The final point model is refit on all 4,000 labeled rows, so the interval is a historical residual reference, not a valid guaranteed-coverage split-conformal construction for the served model. The UI states this limitation. Negative lower demand bounds are clipped at zero.

If a point forecast is below 200 kW but its upper reference bound reaches 200 kW, it gets a threshold-watch diagnostic. This does not alter the official independent overload rule, which uses the point prediction. QuickML forecasts get no local interval because the remote model's errors have not been calibrated.

## Battery engineering

The challenge's demand and evening rules always determine mode. Battery feasibility does not rewrite these rules. A shortfall identifies demand scheduled to storage that cannot be delivered within its energy, output-power, efficiency, and protected-reserve limits.

Capacity advice uses bounded bisection for the smallest energy capacity that covers the fixed hourly plan, using the chosen starting SOC, reserve, charging rate, and efficiency. Required discharge power is calculated separately. An impossible starting-energy assumption returns no finite recommendation. This is a forecast-specific feasibility estimate, not asset sizing across a year or a cost optimization.

The scenario API reuses a saved, browser-scoped forecast. It does not make new QuickML requests, alter demand, or switch the official policy. It reports baseline/candidate shortfall, ending SOC, and planned load served. The chart overlays both simulated SOC trajectories.

## Product changes

- Light operations workspace with a desktop navigation sidebar and responsive top navigation on narrower screens.
- Readable navigation and typography; large demand and SOC charts; useful hour selection.
- Immediate risk summary linking directly to capacity testing.
- Model comparison and research references visible in the application.
- Data provenance and local/QuickML distinctions retained. No invented savings, live connections, or physical control claims.
