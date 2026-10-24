# Final submission steps

The separate GridLens Catalyst project, trained and published QuickML model, public AppSail website, durable Data Store history and live 1,000-row official self-test are complete.

Public app: https://gridlens-50047133296.development.catalystappsail.in

1. Open the public app and review its live QuickML forecast, input form, CSV upload, source-switching signals and overload alerts.
2. Submit this public app URL and GridLens_Submission.zip (or a public repository containing the same source).
3. Include the supplied README and configured predict.py. The original evaluator returned SUCCESS; validation/ contains its transcript, a full 1,000-row live prediction CSV and hashes.
4. Complete the organizer’s form before 28 October 2026. No precise cutoff time was supplied in the email.

No account password, OAuth token or endpoint secret should be put in chat or in the submission ZIP. The app uses managed server authentication. Deployment was completed through the authenticated console; the local CLI device login was not completed and is not required to use the live app or submission script.

See REQUIREMENTS_AUDIT.md for the required-feature mapping. Slate and Stratus are recommended architecture choices in the brief; AppSail is explicitly accepted for the required public app URL. This implementation serves the frontend and backend together on AppSail and persists parsed telemetry and forecasts in Data Store.
