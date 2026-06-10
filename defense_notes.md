# Defense Notes

## 1. One-Sentence Contribution
We provide a reproducible pipeline to estimate market reactions to corporate 10-K filings using an event-time framework, specifically testing text-based AI communication measures among Fortune 100 firms.

## 2. What This Study Measures
This study measures Cumulative Abnormal Returns (CAR) and Abnormal Volume around 10-K filing dates, and tests their association with AI disclosure intensity, risk-related topic shares, and risk orientation.

## 3. What This Study Does Not Measure
This study does **not** measure internal AI adoption or operational effectiveness. It strictly focuses on external communication via regulatory filings.

## 4. Why This Is an Event-Study Design
The event-study design (using the market model) allows us to isolate short-term valuation changes and trading activity specifically associated with the public release of the 10-K report.

## 5. Why This Is Not a Strong Causal-Effect Claim
While we use an event-time design, 10-K reports bundle many types of information. We find that market reactions are not statistically significantly explained by AI measures alone, which suggests that other information in the report (or prior expectations) may dominate the market response.

## 6. How to Defend the Market Data Source
`FinanceDataReader` was used as a robust fallback to ensure 100% reproducible data fetching for US-listed firms when other APIs encounter environment-specific blocks.

## 7. How to Defend the 10-K Filing Date as Event Date
The 10-K filing is the timestamped moment when detailed strategic and risk-related text becomes legally public, making it the ideal window to measure the impact of disclosure-based variables.

## 8. How to Defend the AI Communication Variables
The variables are transparently derived from a machine-learning (Topic Modeling) pipeline, offering an objective way to partition "AI talk" into intensity and risk-thematic dimensions without human coding bias.

## 9. Expected Critiques and Responses
- **"Why are the results not significant?"**
  - *Response:* For Fortune 100 firms, AI strategies may already be "priced in" via prior earnings calls, or the AI disclosure in the 10-K is not providing a "surprise" signal strong enough to move the needle relative to other bundled financial data.
- **"Is the CIK merge reliable?"**
  - *Response:* Yes, we implemented a multi-stage normalization (zero-padding CIKs, ticker cleaning, date-matching) to ensure the 272/273 events were correctly joined with their corresponding AI metrics.
- **"Does no significance mean AI doesn't matter?"**
  - *Response:* No, it means that *variation in the intensity of disclosure in the 10-K* does not uniquely explain short-term abnormal returns for these specific firms in this specific window.

## 10. Safe Presentation Language
- **Use:** "Associated with," "estimated association," "filing-window trading activity," "no statistically significant evidence of association in this sample."
- **Avoid:** "AI caused the stock to drop," "Market ignored AI," "Direct proof of adoption."
