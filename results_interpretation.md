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
The regression models link AI-disclosure variables (`AI_Related_Disclosure_Intensity`, `AI_RiskRelated_Topic_Share`, `AI_Risk_Orientation_Proxy`) to market outcomes. For all primary models, we utilized **Firm Fixed Effects** and **Year Fixed Effects** with **firm-clustered standard errors** (N=272).

### Key Findings:
- **AI Disclosure Intensity:** No statistically significant association with CARs across any window. For `CAR_0_p1`, the coefficient is -0.0147 (p = 0.181).
- **AI Risk-Related Topic Share:** No statistically significant association with CARs. For `CAR_0_p1`, the coefficient is -0.0379 (p = 0.110), showing a marginal but non-significant negative association.
- **AI Risk Orientation Proxy:** No statistically significant association with market reactions.

Overall, while there is a general market response to the 10-K filing (elevated volume), we do not find statistically significant evidence that the specific intensity or tone of AI-related disclosures drives these reactions in the short-term window for Fortune 100 firms.

## 6. Placebo Checks
Pre-filing placebo checks (`CAR_m10_m6`, `CAR_m5_m2`, `AbnormalVolume_m5_m2`) were also estimated. No significant associations were found in the placebo windows, supporting the interpretation that the observed filing-window movements are likely related to the disclosure event itself rather than pre-existing trends.

## 7. Model Diagnostics
- **Market Data Diagnostics:** 272 events were successfully estimated. 1 event failed due to an insufficient estimation window.
- **Regression Diagnostics:** Models were successfully estimated using a cascade of fixed-effect specifications. 272 usable observations were successfully merged using normalized CIK and filing date keys.

## 8. Interpretation Summary
The event-study confirmed significant capital market information processing (abnormal volume) around 10-K filings. However, the short-window abnormal returns are not systematically explained by the variation in AI-related communication intensity or risk-framing. This suggests that the market may already have priced in the AI strategic orientation of these top-tier firms prior to the formal 10-K filing, or that the AI-specific signals are overshadowed by other bundled financials in the report.

## 9. Limitations
- AI disclosure variables are text-based communication proxies, not direct AI adoption measures.
- Topic labels are machine-generated/topic-derived labels, not human-validated coding.
- Sector categories are approximate SEC SIC-derived NAICS enrichment.
- Short-window event studies may not capture long-term strategic value changes related to AI disclosures.