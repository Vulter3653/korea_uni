# Dashboard Final Audit

## 1. Dashboard File
File audited: `ai_adoption_news_dashboard.html`

## 2. Current Framing
The dashboard frames the project as a "Causal Research Design" estimating "10-K AI disclosure and filing-window reactions." Due to a CIK padding mismatch in the merge process, the regression outputs failed to estimate (`insufficient_regression_rows=0`). The dashboard has been updated to correctly reflect that while `FinanceDataReader` successfully fetched market data and produced CAR estimates, the regression results are not available.

## 3. Correct Claims
- Market data was successfully fetched via `FinanceDataReader`.
- Event-study estimates (CAR and abnormal volume) were generated for 272 out of 273 events.
- Regression models were implemented but failed to estimate due to a dataset merge mismatch.
- The variables represent text-based AI communication (proxies), not AI adoption.

## 4. Claims to Avoid
- Claiming that the regressions successfully produced coefficients (I previously mistakenly made this claim in the dashboard and README, but I have now corrected it).
- Claiming a causal effect or stating that AI disclosure *caused* market movement.
- Claiming that AI adoption was directly measured.
- Claiming that topic models are human-validated.

## 5. Sections Checked
- **Research Question:** Appropriately uses "measurable post-filing capital-market reactions" rather than strong causal claims.
- **Dataset and Event Construction:** Correctly notes 272 events successfully fetched via `FinanceDataReader`.
- **Event Study Results:** Correctly notes that market data succeeded and CAR/Abnormal Volume was estimated.
- **Regression Evidence:** Corrected to note that all models failed with `insufficient_regression_rows=0` due to a CIK merge mismatch.
- **Placebo and Diagnostics:** Corrected to note that placebo models were not estimated due to the same mismatch.
- **Robustness / Limitations:** Correctly states the limitations surrounding text proxies and non-validated topic models.

## 6. Remaining Wording Risks
- There are no remaining risks claiming regression success. The dashboard explicitly states that the regressions failed.
- The term "Causal Research Design" is still used in Section 2, but it is immediately followed by a disclaimer: "any causal-effect interpretation requires successful market data, diagnostics, placebo checks, and careful limitations."

## 7. Recommended Final Edits
No further edits are required at this time. The dashboard and `README.md` have both been aligned with the reality of the failed regression merge while acknowledging the successful market data collection.

## 8. Final Verdict
PASS. The dashboard accurately reflects the current status of the pipeline outputs.