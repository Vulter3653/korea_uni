# Results Interpretation

## 1. Research Question
Do firms' AI-related 10-K disclosures and topic-derived AI communication measures relate to abnormal market reactions around the 10-K filing date?

## 2. Event-Study Sample
The sample is based on the Fortune 2025 Top 100 firms. We have an observed 10-K text sample of 273 firm-year events. Market data collection via `FinanceDataReader` successfully retrieved sufficient price data for 272 of these 273 events.

## 3. Market Reaction Outcomes
We analyze market reactions around the 10-K filing date using:
- **Cumulative Abnormal Returns (CAR):** Estimated using a market model with US500 as the benchmark. Windows include [-1, +1], [0, +1], [0, +3], and [0, +5].
- **Abnormal Volume:** Estimated as the standardized log-volume relative to the estimation window. Windows include [0, +1], [0, +3], and [0, +5].

## 4. Descriptive Event-Study Results
For the 272 successfully estimated events, the descriptive statistics for market reactions are as follows:

| Window | Mean | Median | Std. Dev. | Min | Max |
| --- | --- | --- | --- | --- | --- |
| `CAR_m1_p1` | 0.0030 | 0.0027 | 0.0485 | -0.2672 | 0.2442 |
| `CAR_0_p1` | 0.0031 | 0.0032 | 0.0441 | -0.2580 | 0.2124 |
| `CAR_0_p3` | 0.0028 | 0.0033 | 0.0471 | -0.3173 | 0.1822 |
| `CAR_0_p5` | 0.0024 | 0.0038 | 0.0524 | -0.2972 | 0.2072 |
| `AbnormalVolume_0_p1` | 0.6070 | 0.3605 | 1.1228 | -1.6578 | 4.6128 |
| `AbnormalVolume_0_p3` | 0.4614 | 0.3194 | 0.8892 | -1.3435 | 4.3411 |
| `AbnormalVolume_0_p5` | 0.3704 | 0.3343 | 0.7832 | -1.2936 | 4.0436 |

On average, firms experience slightly positive abnormal returns around the filing window (approx. 0.3%). Abnormal volume is generally elevated, with the [0, +1] window showing volume approximately 0.61 standard deviations above the pre-filing mean, indicating significant information processing by the market.

## 5. Regression Evidence
The regression models linking AI-disclosure variables (`AI_Related_Disclosure_Intensity`, `AI_RiskRelated_Topic_Share`, `AI_Risk_Orientation_Proxy`) to market outcomes were **not estimated**. 

During the construction of the analysis dataset, a firm identifier formatting mismatch (CIK padding) prevented the successful merging of the AI communication metrics with the CAR estimates. As a result, the regression models encountered 0 usable observations (`insufficient_regression_rows=0`). Thus, no statistical inference or coefficients can be provided at this stage.

## 6. Placebo Checks
Pre-filing placebo checks (`CAR_m10_m6`, `CAR_m5_m2`, `AbnormalVolume_m5_m2`) also failed to estimate due to the same identifier merge issue. Consequently, we cannot currently evaluate whether the market reactions are strictly isolated to the post-filing window.

## 7. Model Diagnostics
- **Market Data Diagnostics:** 272 events were successfully estimated. 1 event failed due to an insufficient estimation window (fewer than 60 days). The fallback estimation windows were effectively utilized where full 250-day histories were unavailable.
- **Regression Diagnostics:** All 10 baseline, FE, and SE specified models resulted in a `failed` status due to 0 observations (`insufficient_regression_rows=0`).

## 8. Interpretation Summary
The descriptive event-study outputs confirm that there is actionable market movement—particularly elevated abnormal volume—around the 10-K filing dates for these Fortune 100 firms. However, because the regression models failed to estimate due to a dataset merge constraint, we cannot determine whether the intensity or tone of AI-related disclosures correlates with these market movements. 

## 9. Limitations
- AI disclosure variables are text-based communication proxies, not direct AI adoption measures.
- Topic labels are machine-generated/topic-derived labels, not human-validated coding.
- Sector categories are approximate SEC SIC-derived NAICS enrichment, not fully verified firm-level NAICS classifications.
- Causal associations between AI communication and CARs remain unestimated due to a merge error in the current pipeline run. No conclusions about the causal effect of AI disclosures on stock prices can be drawn.
