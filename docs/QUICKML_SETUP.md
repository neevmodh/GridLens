# QuickML setup and verification

The included deployment already has a trained, published endpoint. `predict.py` uses its hosted live prediction relay by default; no OAuth setup is needed for that path. The instructions below explain reproducing the deployment or configuring direct OAuth inference.

## 1. Choose a consistent training schema

The most direct option is uploading the provided `data/train_telemetry.csv` in a QuickML regression pipeline with target `target_demand_kw`. Make sure timestamp preprocessing extracts useful hour/time information instead of treating each timestamp as an unrelated category. Keep the target out of the input feature set.

An alternative is the already prepared `data/quickml_training.csv`, generated using:

```sh
python3 scripts/prepare_quickml.py
```

It contains temperature, humidity and solar features, heating/cooling interactions, hour sine/cosine harmonics, hour indicators, hour-specific cooling responses, weekend, evening, and the training target. This has no unknown future-demand features and requires no previous demand readings during inference. Set `QUICKML_FEATURE_SCHEMA=engineered` for this choice. The same `advanced_features()` function in `energy/features.py` constructs features for inference. The export was updated for version 2; train the model on this current export rather than mixing it with an earlier schema.

Use a chronological validation split when possible. Select the regression algorithm and tuning by validation RMSE; do not assume the local ridge model's score applies to QuickML.

## 2. Publish the endpoint

In Catalyst QuickML, create an endpoint from your trained model and publish its intended version. The endpoint console shows its URL, key, required headers, and a sample request/response. Run that built-in test before integrating the application.

Follow the [official endpoint guide](https://docs.catalyst.zoho.com/en/quickml/help/pipeline-endpoints/).

## 3. Configure server environment

Copy `.env.example` to `.env` locally. For a linked AppSail deployment, environment values are applied from `app-config.json`; redeploying can replace console-only settings. Keep a secret-bearing deployment configuration outside the public source archive and repository. Never put credentials in frontend JavaScript, chat, or source ZIP.

Required values:

| Variable | Value |
| --- | --- |
| `QUICKML_ENDPOINT_URL` | Published HTTPS inference URL from the endpoint console |
| `QUICKML_ENDPOINT_KEY` | Endpoint key for `X-QUICKML-ENDPOINT-KEY` |
| `ZOHO_ORG_ID` | Organization identifier used in `CATALYST-ORG` |
| `QUICKML_ENVIRONMENT` | `Development` or `Production`, matching the endpoint |
| `QUICKML_FEATURE_SCHEMA` | `raw` for original training CSV, `engineered` for the prepared CSV |
| `QUICKML_REQUEST_MODE` | `single` for one feature object per request, or `batch` if the endpoint supports lists |
| `QUICKML_INPUT_KEY` | Defaults to `data`, the official QuickML prediction API wrapper |

The official prediction API uses `POST https://api.catalyst.zoho.in/quickml/v1/project/{project_id}/endpoints/predict` with `{"data": {...features...}}` and returns `{"result": ["<number>"], "pipeLineType": "prediction", "status": "success"}`. Confirm the published endpoint's sample before changing to batch mode. Legacy local `CATALYST_ORG_ID` / `CATALYST_ENVIRONMENT` settings remain accepted, but new deployments use the names above to avoid Catalyst's reserved variable prefix. The managed `X_ZOHO_CATALYST_ORG_ID` is also accepted when no explicit organization is set.

### OAuth

For the hosted website, `QUICKML_AUTH_MODE=catalyst` uses Zoho's official Python SDK with the AppSail gateway's request credentials. Set `QUICKML_PROJECT_ID` to the project's actual identifier, `ZOHO_ORG_ID` to the organization ID and `QUICKML_ENDPOINT_KEY` to its published endpoint key. The app verifies that the gateway project matches. No refresh token is needed for this hosted mode. The app supplies missing SDK organization/API defaults without overriding managed runtime values. The standalone evaluator uses the hosted relay, or direct OAuth as described below. Set `QUICKML_AUTH_MODE=oauth` for direct local OAuth inference.

Obtain OAuth authorization for scope `QuickML.deployment.READ` using the Zoho API Console and the correct data center. For a short connection test, `ZOHO_ACCESS_TOKEN` can hold a current access token. This expires and is unsuitable for unattended judging.

For the lasting submission use:

```dotenv
ZOHO_ACCOUNTS_URL=https://accounts.zoho.in
ZOHO_CLIENT_ID=<your-client-id>
ZOHO_CLIENT_SECRET=<your-client-secret>
ZOHO_REFRESH_TOKEN=<your-refresh-token>
```

Leave `ZOHO_ACCESS_TOKEN` empty when using refresh. Use your actual data center's official Zoho Accounts URL. Tokens are cached in process memory and refreshed before expiry. An expired or invalid explicitly configured access token returns a live error rather than falling back locally.

The client sends the documented `X-QUICKML-ENDPOINT-KEY`, `Authorization: Zoho-oauthtoken ...`, `CATALYST-ORG`, and `Environment` headers.

## 4. Verify both interfaces

Restart the local server after changing `.env`. In **Model & connection**, “Credentials present” means the settings exist; it does not prove the endpoint is reachable.

Use **New forecast**, select **Zoho Catalyst QuickML**, and run 24 rows. A successful response must show **QuickML forecast** at the top of the dashboard. Confirm predictions agree with the model console on the same inputs.

Then run:

```sh
python3 predict.py --input sample_test_input.csv --output predictions.csv
```

This must return 1,000 numeric predictions in the supplied timestamp order. In single-record mode, this makes 1,000 endpoint requests with up to four simultaneous requests; allow sufficient runtime and endpoint quota. This project’s deployed batch mode has been verified on all 1,000 supplied test rows. The hosted relay divides these into ten batches of at most 100 records; direct single-record mode remains available for other endpoints.

Install evaluation-only dependencies and run the supplied `test_eval.py` without the local flag. If inference response structure differs, adapt `extract_predictions()` in `energy/quickml.py` using the actual sample, and add a response fixture test before submitting.

At no point does a failed live call silently return the local preview model.

## Durable history configuration

The hosted app uses `GRIDLENS_HISTORY_TABLE=92358000000019001`. Its `GridLensRuns` table stores RunKey, a SHA-256 SessionKey, UTC CreatedAt, a summary and a compressed forecast payload. Table scopes are USER for both roles, with SELECT/INSERT only for the server's App Administrator and no App User operations. Leave the variable empty for local SQLite development. `GRIDLENS_PUBLIC_ORIGIN` must equal the public HTTPS app origin.
