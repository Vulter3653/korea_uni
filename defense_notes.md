# Defense Notes

## 1. One-Sentence Contribution
We provide a scalable, automated pipeline to estimate market reactions to corporate 10-K filings using an event-time framework, focusing on the text-based communication of AI topics among Fortune Top 100 firms.

## 2. What This Study Measures
This study measures the market's response (via Cumulative Abnormal Returns and Abnormal Volume) during the days immediately following a 10-K filing. It also measures the intensity, topic distribution, and tone of AI-related keywords within the text of those 10-K filings.

## 3. What This Study Does Not Measure
This study does **not** measure actual firm-level AI adoption, capital expenditures on AI, or the true operational impact of AI technologies. It strictly measures corporate *communication* regarding AI.

## 4. Why This Is an Event-Study Design
An event-study design allows us to isolate the market's reaction to a specific information disclosure event (the 10-K filing). By analyzing abnormal returns and volume in tight windows (e.g., [0, +1] days), we can more cleanly associate market movements with the release of the report rather than long-term confounding macro trends.

## 5. Why This Is Not a Strong Causal-Effect Claim
Even with a narrow event window, a 10-K filing contains vast amounts of information (earnings, strategic shifts, macro outlooks). We cannot definitively prove that the market reaction was *caused* specifically by the AI disclosures rather than other concurrent disclosures in the same report. Furthermore, AI disclosure is endogenous; firms may strategically choose to highlight AI when they have other positive news.

## 6. How to Defend the Market Data Source
We utilized `FinanceDataReader` as a robust fallback mechanism to retrieve US500 benchmark data and firm-level adjusted closing prices. This ensures the reproducibility of the pipeline even when standard APIs like `yfinance` encounter network or timezone parsing issues.

## 7. How to Defend the 10-K Filing Date as Event Date
The 10-K filing date is the legally mandated, time-stamped moment when the comprehensive text containing our AI measures becomes public information. While some financials may be pre-released in earnings calls, the detailed risk factors and strategic discussions—where AI communication is predominantly found—are formalized in the 10-K.

## 8. How to Defend the AI Communication Variables
Our AI variables (`AI_Related_Disclosure_Intensity`, `AI_RiskRelated_Topic_Share`) are transparent, reproducible text proxies. While they rely on machine-derived topics rather than human-validated coding, they offer a scalable, objective measure of how prominently management chose to feature AI terminology in their regulatory filings.

## 9. Expected Critiques and Responses
- **"Is this a true causal analysis?"** 
  - *Response:* No, it is a quasi-experimental event-time association. We observe whether AI communication correlates with market reactions, but we explicitly disclaim strong causal identification due to the bundled nature of 10-K information.
- **"Are you measuring AI adoption?"**
  - *Response:* No, we are measuring AI *disclosure* and *communication*. We proxy how much management talks about AI, not their internal infrastructure.
- **"Are your topic labels validated?"**
  - *Response:* The topic labels are machine-generated heuristics designed for scalability. We do not claim they are perfectly human-validated, but they provide a systematic baseline for textual variation.
- **"Can we trust FinanceDataReader?"**
  - *Response:* Yes, it is a widely used and reliable API for historical market data. We also implemented a local CSV fallback to ensure full transparency and auditability of the data if external APIs fail.
- **"Can we attribute the market reaction to AI disclosure?"**
  - *Response:* Not definitively. The 10-K is a bundled disclosure. We use placebo checks and multivariate controls to mitigate this, but unobserved confounding information within the 10-K remains a limitation.
- **"Is a sample of Fortune Top 100 firms generalizable?"**
  - *Response:* The findings are specific to large-cap, highly scrutinized firms. This is a feature, not a bug, as these firms are market leaders in strategic communication, but we acknowledge the results may not generalize to small-cap firms.

## 10. Safe Presentation Language
- **Use:** "Event-study evidence," "filing-window abnormal return," "post-filing market reaction," "market-model abnormal return," "quasi-experimental event-time design."
- **Avoid:** "Causal effect," "caused by AI disclosure," "direct measure of AI adoption," "human-validated topic labels."