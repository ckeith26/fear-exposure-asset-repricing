# Title

**Flood Map Revisions and Housing Market Capitalization: Evidence from FEMA LOMRs and ZIP-Code Home Values**

## Abstract

This paper studies how FEMA Letters of Map Revision (LOMRs) affect local housing values by changing official flood-risk designations and, in some cases, the set of properties subject to mandatory flood-insurance requirements. I assemble a ZIP-by-quarter panel from 2009–2022 that combines Zillow Home Value Index data with FEMA LOMR records, NFIP policies and claims, county labor-market controls, and several heterogeneity measures. Using a staggered difference-in-differences event-study design with ZIP and county-by-year fixed effects, I find that home values in treated ZIP codes decline gradually after a first in-window LOMR, with the largest baseline effect appearing about four or more years after treatment. The average binary treatment effect is modest, but effects become substantially larger in areas with greater pre-treatment NFIP policy penetration. Mechanism tests show limited average movement in insurance take-up overall, though downzoned areas exhibit some post-treatment declines in NFIP policies. Additional heterogeneity analyses by disclosure laws and political lean are informative but more tentative. In particular, estimates are weaker in Republican-leaning counties, but those interaction results fail pre-trend tests and should therefore be interpreted as descriptive rather than causal. Overall, the evidence is most consistent with gradual capitalization of flood-risk reclassification in high-exposure housing markets rather than an immediate uniform repricing across all treated areas.

---

# 1. Introduction

## 1.1 Motivation

Flood risk is a central determinant of housing-market outcomes in coastal and riverine communities, yet much of that risk is mediated through public information systems and regulatory classifications rather than through observed flood events alone. FEMA flood maps determine whether properties fall inside the Special Flood Hazard Area (SFHA), which affects disclosure, lending, insurance, and buyer beliefs. When FEMA issues a LOMR, it updates the official map based on new engineering information, physical changes, or corrected modeling. These revisions may alter beliefs about flood risk even when no flood has occurred.

## 1.2 Research Question

This paper asks: **Do FEMA LOMRs reduce local home values, and are those effects stronger where flood-risk exposure, regulation, or local beliefs make the information more salient?**

## 1.3 Main Hypothesis

The core hypothesis is that LOMRs lead to downward repricing of homes when they reveal or formalize greater flood risk. The expected effect should be strongest where flood-insurance exposure is already high, where map revisions move parcels across the SFHA boundary, and where institutions make the information harder to ignore.

## 1.4 Contribution

This paper contributes in four ways.

First, it studies a regulatory information shock rather than a realized disaster shock.
Second, it links FEMA map revisions to housing values at the ZIP-quarter level over a long panel.
Third, it distinguishes between average effects and exposure-scaled effects using pre-treatment NFIP penetration.
Fourth, it evaluates several heterogeneity channels, including upzoning/downzoning, disclosure laws, and political lean.

## 1.5 Preview of Results

The baseline event study suggests modest but increasingly negative post-treatment effects on log real home values, with the largest estimate at four or more years after treatment. The average binary treatment effect is not large in a simple TWFE DiD, but the dynamic event-study profile is more informative. Intensity-weighted specifications show substantially larger declines in high-exposure ZIP codes. Mechanism tests on NFIP policies and claims provide limited support for an immediate universal insurance channel, though some directional effects emerge in downzoned areas. Exploratory political heterogeneity is interesting but does not pass pre-trend diagnostics, so it is not treated as a core causal result.

---

# 2. Institutional Background

## 2.1 FEMA Flood Maps and LOMRs

FEMA’s Flood Insurance Rate Maps classify land into flood-risk zones used for insurance and lending purposes. A LOMR is an official revision to an effective flood map, often based on new topographic, hydrologic, or engineering information. In practice, LOMRs can move parcels into or out of regulated flood zones or revise base flood elevations without crossing the SFHA boundary.

## 2.2 Why LOMRs Should Affect Housing Markets

LOMRs matter through at least three channels:

1. **Information channel**: buyers and lenders learn that official flood risk is different than previously believed.
2. **Insurance-cost channel**: if a property enters the SFHA, mandatory flood insurance may apply for federally backed mortgages.
3. **Disclosure/regulatory salience channel**: state disclosure laws, lenders, insurers, and local institutions may amplify or mute how strongly the information affects pricing.

## 2.3 Why Effects May Be Heterogeneous

Not all map revisions are equally important. Effects may be larger where:

* more households are already exposed to flood insurance,
* revisions cross the SFHA boundary,
* states require stronger disclosure,
* local political or informational environments change how official risk information is processed.

---

# 3. Related Literature

## 3.1 Natural Hazard Risk and Housing Markets

This paper connects to work on how environmental and disaster risk capitalizes into housing prices, especially research on flood zones, coastal risk, and climate exposure.

## 3.2 Information Disclosure and Asset Prices

It also relates to literature showing that public information and mandated disclosure can affect real-estate values when information is costly, uncertain, or previously ignored.

## 3.3 Difference-in-Differences with Staggered Treatment

Methodologically, the paper engages with the recent literature on staggered DiD, including concerns about TWFE weighting and heterogeneity bias, motivating both event-study presentation and heterogeneity-robust robustness checks.

## 3.4 Positioning

Relative to the literature, this project focuses on **official flood-map revision events**, rather than realized storms or broad climate beliefs, and asks whether housing markets respond gradually to new regulatory information.

---

# 4. Data

## 4.1 Core Panel Structure

The main estimation sample is a ZIP-by-quarter panel running from 2009–2022. The raw monthly panel is collapsed to quarters because Zillow’s home-value series is smoothed and serially correlated at the monthly level. The quarterly estimation sample contains:

* **228,005 ZIP-quarter observations** (228,002 in regressions after dropping NAs)
* **4,272 ZIP codes in the estimation sample**
* **56 quarters in the original quarterly panel before sample restrictions**

The paper should state these counts clearly in the text and repeat them in the summary-statistics discussion.

## 4.2 Data Sources

### 4.2.1 Zillow Home Value Data

The primary outcome is Zillow’s ZIP-level home value index, converted into real terms and logged for the main specifications.

### 4.2.2 FEMA LOMR Data

Treatment is based on the first effective LOMR observed within the sample window. The data also identify whether the ZIP is ever treated, whether it is treated during the window, whether it was already treated before the sample begins, and whether the revision changes flood-zone risk direction.

### 4.2.3 NFIP Insurance Data

NFIP data provide policy counts, average premiums, claims counts, claims paid, and related insurance exposure measures.

### 4.2.4 County Controls

County-level unemployment rates are merged as a macro control. Election-based political measures are also added at the county level.

### 4.2.5 Disclosure Laws

State disclosure-law indicators distinguish states with stricter mandatory flood-disclosure regimes from other states, with both strict and broad definitions used in robustness checks.

## 4.3 Sample Restrictions

The estimating sample excludes:

* ZIPs already treated before the analysis window,
* ZIPs with multiple LOMRs,
* ZIPs with zero or missing population,
* cohorts outside the valid window for some robustness estimators.

These restrictions are justified as necessary for clean treatment timing and interpretable event-time comparisons.

> **Output:** `s01_sample_construction.tex` / `.png`

## 4.4 Descriptive Patterns to Add Before Regressions

Per the paper guidance, the outline should explicitly commit to showing the data before regressions. The paper should include:

* a table of summary statistics,
* frequency tables for treatment timing and sample composition,
* histograms of key variables,
* plots of treatment timing and event-study coefficients,
* tables showing means by treatment status and by exposure groups.

### 4.4.1 Recommended Descriptive Commands / Outputs

* `tab year`
* `tab fundtype` analog adapted to paper variables, e.g. `tab ever_treated`, `tab event_bin`, `tab zone_risk_direction`
* `table year, c(mean ln_real_zhvi n ln_real_zhvi)`
* histogram of `policy_intensity`
* histogram of treatment timing
* bar charts or tables by intensity quartile
* scatter or category-mean plots where useful

---

# 5. Variable Construction

## 5.1 Outcome Variables

### 5.1.1 Main Outcome

The primary dependent variable is `ln_real_zhvi`, the log of real ZIP-level Zillow home values.

### 5.1.2 Alternative Outcomes

Supporting outcomes include:

* `ln_policies`
* `ln_claims`
* unemployment rate as a placebo outcome

## 5.2 Treatment Variables

### 5.2.1 Binary Post-LOMR Indicator

`treated` equals one after the first in-window LOMR.

### 5.2.2 Event-Time Indicators

The event study bins treatment into annual windows from at least three years before treatment through four or more years after treatment, with the year immediately before treatment omitted as the reference period.

### 5.2.3 Intensity Measures

Two treatment-intensity concepts are used:

* **policy intensity**: pre-treatment NFIP policies per population
* **geographic intensity**: LOMR polygon area relative to ZIP area

## 5.3 Heterogeneity Variables

### 5.3.1 Risk Direction

Indicators for upzoned and downzoned revisions distinguish whether the LOMR moves land into or out of the SFHA.

### 5.3.2 Disclosure Laws

Strict and broad disclosure-law definitions identify states where flood-risk information is more likely to be formally disclosed in transactions.

### 5.3.3 Political Lean

A county-level Republican indicator is defined using the median county Republican two-party vote share.

---

# 6. Empirical Strategy

## 6.1 Baseline Event-Study Specification

The main specification is a staggered event-study DiD of the form:

[
\ln(\text{Real ZHVI}*{zct}) = \sum*{\tau \neq -1}\beta_\tau \cdot 1{event\ time = \tau}*{zt} + X*{ct}'\Gamma + \alpha_z + \delta_{cy} + \varepsilon_{zct}
]

where:

* ( \alpha_z ) are ZIP fixed effects,
* ( \delta_{cy} ) are county-by-year fixed effects,
* ( X_{ct} ) includes county unemployment and selected NFIP controls,
* standard errors are clustered at the county level,
* the regressions are population-weighted in the main specification.

## 6.2 Identification

Identification comes from comparing changes in home values in treated ZIP codes around the timing of a first LOMR to changes in never-treated ZIP codes, after absorbing permanent ZIP differences and county-specific time shocks.

## 6.3 Parallel Trends

The credibility of the design depends on pre-treatment coefficients being jointly close to zero. The baseline event study passes the joint pre-trend test, which supports the main design.

> **Output:** `s10_parallel_trends.png` / `.gph` (event-time pre-treatment coefficients with 95% CIs and F-test p-value)

## 6.4 Why Event Study Instead of Only TWFE

A single post-treatment coefficient obscures the timing of effects and is vulnerable to composition issues in staggered settings. The event-study design provides both a dynamic treatment path and a direct diagnostic for pre-trends.

---

# 7. Descriptive Statistics and Preliminary Evidence

## 7.1 Summary Statistics Table

The paper should present a full summary-statistics table early, with a paragraph above the table explaining:

* what the sample is,
* what each variable means,
* which variables are outcomes, treatments, controls, and heterogeneity measures,
* how many ZIPs and quarters are represented.

> **Output:** `s02_summary_stats.tex` / `.csv` / `.png`

## 7.2 Balance Table

A treated-versus-control pre-treatment balance table should be presented next, along with a paragraph interpreting the main differences. The current estimates suggest treated areas are denser, somewhat smaller in population, and differ in unemployment, NFIP policies, premiums, and SFHA share.

> **Output:** `s03_balance_table.tex` / `.csv` / `.png`

## 7.3 Figures Before Regressions

The paper should include a small descriptive figure set before the main regressions:

* histogram of first LOMR year,
* histogram of policy intensity,
* frequency chart for risk direction,
* table or bar chart of means by intensity quartile.

> **Output:** `s10_treatment_timing_hist.png` / `.gph` (treatment timing histogram)

## 7.4 Means by Exposure Groups

Consistent with the guidance, the paper should show some of the basic pattern in means before moving to regressions. For example:

* average home values by intensity quartile,
* average post-treatment changes by quartile,
* means by upzoned/downzoned categories.

This helps the reader see the empirical pattern before the formal event-study design.

---

# 8. Main Results

## 8.1 Baseline Event Study

The baseline event-study results are the centerpiece of the paper. The pre-treatment coefficients are small and jointly insignificant, while the post-treatment coefficients become more negative over time. The largest estimate occurs in the four-plus-years bin and is around a 2.8 percent decline in real home values (exp(-0.0287) - 1).

## 8.2 Interpretation

The dynamic pattern suggests gradual capitalization rather than a sharp one-quarter repricing. That is consistent with a housing market that learns slowly, updates through transactions, and processes flood-map revisions gradually.

## 8.3 Table Design

The main regression table should include a paragraph immediately above it explaining:

* dependent variable: `ln_real_zhvi`
* omitted category: the year immediately before treatment
* difference between columns: no controls, main controls, full controls
* fixed effects and clustering
* interpretation of coefficients as proportional changes in home values relative to the pre-treatment baseline

## 8.4 Event-Study Figure

The coefficient plot should appear directly after the main table and be discussed in detail in the text.

> **Output (table):** `s04_regression_table.tex` / `.csv` / `.png` (3-spec regression: no controls, main controls, full controls)
> **Output (figure):** `s05_event_study_main.png` / `.pdf`, `s05_event_study_coefficients.csv`
> **Output (TWFE DiD):** `s07_did_twfe.tex` / `.png` (simple binary post-treatment TWFE for comparison)

---

# 9. Treatment Intensity and Dose Response

## 9.1 Motivation

A binary treatment may understate effects because many ZIPs contain only a small share of households directly exposed to flood-insurance or flood-zone revisions. Scaling treatment by pre-treatment NFIP penetration captures the idea that LOMRs should matter more where more of the housing stock is exposed.

## 9.2 Intensity-Weighted Specification

The intensity-weighted event study shows materially larger negative post-treatment effects, especially in later post-treatment periods. This is one of the strongest results in the paper.

## 9.3 Quartile-Based Dose Response

The nonparametric quartile specification allows the data to show whether the effect is monotonic across low- and high-exposure ZIPs.

## 9.4 Interpretation

The quartile results suggest that effects are concentrated in more exposed places, though the dose-response pattern is not perfectly monotonic across all quartiles and horizons. The text should present that honestly.

> **Output (intensity table):** `s06_regression_intensity.tex` / `.csv` / `.png` (binary vs. intensity-weighted)
> **Output (intensity figure):** `s06_event_study_intensity.png` / `.pdf`, `s06_event_study_intensity_coefficients.csv`
> **Output (quartile table):** `s06b_regression_intensity_quartiles.tex` / `.csv` / `.png`
> **Output (quartile figure):** `s06b_event_study_intensity_quartiles.png` / `.pdf`, `s06b_event_study_intensity_quartiles_coefficients.csv`

## 9.5 Suggested Added Descriptive Table

Before the intensity regressions, add a table of means by intensity quartile. This directly follows the paper guidance and helps motivate why the intensity specification is economically meaningful.

---

# 10. Mechanism: Insurance Market Responses

## 10.1 Why Insurance Is a Mechanism Test

If LOMRs work partly through the mandatory purchase requirement or through revised beliefs about insurable flood risk, NFIP policy counts should respond after treatment.

## 10.2 Policy Outcome Results

The average event study for `ln_policies` shows limited overall response, with only some negative post-treatment estimates reaching significance. This implies that the insurance channel is present at most selectively, rather than strongly in the full treated sample.

## 10.3 Claims as a Falsification / Auxiliary Mechanism Outcome

The claims regressions are best interpreted cautiously. LOMRs should not mechanically cause floods, so claims should not be the primary mechanism. Their role is more diagnostic than central.

## 10.4 Upzoned vs Downzoned Insurance Responses

Splitting the insurance regressions by risk direction is more informative. Downzoned areas show some evidence of policy declines, which is consistent with removal of mandatory insurance requirements. Upzoned areas do not show equally strong increases, suggesting frictions, imperfect compliance, or slow adjustment.

## 10.5 Framing

This section should be written as suggestive mechanism evidence rather than a fully decisive first stage.

> **Output (pooled insurance table):** `s08_regression_insurance.tex` / `.csv` / `.png` (ln_policies + ln_claims)
> **Output (pooled policies figure):** `s08_event_study_policies.png` / `.pdf`, `s08_event_study_policies_coefficients.csv`
> **Output (up/down insurance table):** `s08b_regression_insurance_updown.tex` / `.csv` / `.png`
> **Output (up/down policies figure):** `s08b_event_study_policies_updown.png` / `.pdf`, `s08b_event_study_policies_updown_coefficients.csv`

---

# 11. Heterogeneity Analyses

## 11.1 Upzoned vs Downzoned Home-Value Effects

The paper’s substantive intuition suggests that upzoning should be more negative than downzoning because it imposes or reveals risk more sharply. In the current estimates, however, the home-value heterogeneity is weak, and neither side produces especially strong price responses. This should be framed as a useful null or near-null heterogeneity finding.

> **Output (table):** `s09_regression_updown.tex` / `.csv` / `.png`
> **Output (figure):** `s09_event_study_updown.png` / `.pdf`, `s09_event_study_updown_coefficients.csv`

## 11.2 Disclosure Laws

The disclosure-law interaction tests whether states with stronger mandatory disclosure regimes show larger repricing after map revisions. The estimated interaction terms are weak and jointly insignificant post-treatment in both strict and broad specifications. This section is worth keeping, but it should not be overemphasized.

> **Output (table):** `s09b_regression_disclosure.tex` / `.csv` / `.png`
> **Output (figure):** `s09b_event_study_disclosure.png` / `.pdf`, `s09b_event_study_disclosure_coefficients.csv`

## 11.3 Political Heterogeneity

The Republican interaction produces interesting and economically large estimates in the intensity-based model. The implied pattern suggests weaker negative treatment effects in Republican-leaning counties. However, the pre-treatment interaction terms fail the parallel-trends test, which substantially weakens causal interpretation.

### 11.3.1 How to Write This

This should be presented as:

* an exploratory result,
* suggestive of differential responsiveness to official risk information,
* not a headline causal finding.

### 11.3.2 Why Keep It

Even with failed pre-trends, it is still worth discussing because:

* the effect sizes are large,
* the pattern is substantively relevant,
* it may motivate future work on political trust, disclosure, and risk salience.

But the wording must remain disciplined.

> **Output (table):** `s09c_regression_republican.tex` / `.csv` / `.png`
> **Output (figure):** `s09c_event_study_republican.png` / `.pdf`, `s09c_event_study_republican_coefficients.csv`

---

# 12. Robustness Checks

## 12.1 SFHA-Crossing-Only Sample

Restricting to LOMRs that actually cross the SFHA boundary is a natural robustness exercise because it isolates revisions most likely to change insurance obligations. The estimates become less precise and do not strengthen dramatically, suggesting that the average effect is not driven only by explicit mandate changes.

> **Output (table):** `s09d_regression_sfha_crossing.tex` / `.csv` / `.png`
> **Output (figure):** `s09d_event_study_sfha_crossing.png` / `.pdf`, `s09d_event_study_sfha_crossing_coefficients.csv`

## 12.2 Unweighted Regressions

Unweighted results are smaller and noisier than the population-weighted main specification, which suggests the main effects are more concentrated in larger ZIPs and thicker housing markets.

## 12.3 Geographic Intensity

Using treatment intensity based on LOMR area relative to ZIP area yields weak results. This is useful because it shows that insurance penetration appears to be a more economically relevant exposure measure than purely geographic overlap.

> **Output (12.2 + 12.3):** `s095_robustness_table.tex` / `.csv` / `.png` (main weighted, unweighted, geographic intensity in one table)

## 12.4 Leave-One-Out by State

The leave-one-out exercise helps show whether the main late-period result is driven by any single state.

> **Output:** `s15_leave_one_out_state.csv`

## 12.5 Alternative Clustering

State-level clustering weakens precision but leaves the broad pattern intact.

> **Output:** `s16_event_study_alt_clustering_coefficients.csv`

## 12.6 Goodman-Bacon Decomposition

The Bacon decomposition shows that most identifying weight comes from comparisons involving never-treated units. This supports the idea that the TWFE estimate is not dominated by problematic treated-versus-treated comparisons, though the decomposition should be treated as diagnostic rather than definitive.

> **Output:** `s12_bacon_decomposition.png` / `.pdf`

## 12.7 Callaway and Sant’Anna

The heterogeneity-robust estimator is a useful check, but in the current implementation the event-study aggregation indicates nonzero pre-treatment averages. That means the C&S results should be reported carefully and not used to supersede the cleaner baseline event-study story.

> **Output:** `s13_event_study_cs.png` / `.pdf`, `s13_event_study_cs_coefficients.csv`

## 12.8 Placebo Outcome

The unemployment placebo is problematic because it shows significant pre-trend and post-period movement. This is not a clean placebo success. The section should remain in the paper, but it should be framed as a cautionary diagnostic rather than supportive evidence.

> **Output:** `s14_event_study_placebo.png` / `.pdf`, `s14_event_study_placebo_coefficients.csv`

---

# 13. Discussion

## 13.1 What the Strongest Results Show

The strongest results in the paper are:

* the baseline dynamic decline in home values after LOMRs,
* the stronger effects in intensity-weighted specifications,
* the gradual rather than instantaneous timing.

## 13.2 What the Weak or Mixed Results Show

Several theoretically interesting channels are weaker in the data than expected:

* average insurance take-up effects are limited,
* disclosure-law heterogeneity is weak,
* upzoned/downzoned price heterogeneity is not especially sharp,
* political heterogeneity is interesting but not causally clean.

## 13.3 Economic Interpretation

The most plausible reading is that LOMRs matter primarily as **slow-moving regulatory information shocks**. Market participants do not uniformly reprice immediately, but more exposed markets eventually incorporate the information. That mechanism seems stronger in places where more households are already tied to flood-insurance exposure.

## 13.4 Limits

Important limitations include:

* ZIP-level rather than transaction-level aggregation,
* imperfect mapping from revisions to individual parcel exposure,
* limited ability to separate pure information effects from financing and insurance channels,
* mixed evidence in some placebo and robustness exercises.

---

# 14. Conclusion

This paper studies whether official FEMA flood-map revisions affect housing-market prices. Using a ZIP-by-quarter panel and a staggered event-study design, it finds that first in-window LOMRs are followed by gradual declines in home values, with stronger effects in higher-exposure ZIP codes as measured by pre-treatment NFIP penetration. The average binary effect is modest, but the intensity results show that flood-map revisions matter most where flood-risk regulation is economically salient. Mechanism evidence points only weakly to average changes in insurance take-up, suggesting that the key effect may be broader capitalization of revised risk information rather than a simple insurance-cost shock. Heterogeneity by political lean is substantively interesting but does not satisfy the paper’s diagnostic threshold for causal interpretation. Overall, the results support the view that regulatory flood-risk information can be slowly but meaningfully capitalized into local housing markets.

---

# 15. Tables and Figures Plan

## 15.1 Target Count

Aim for roughly **5–10 tables plus figures**, consistent with the course guidance.

## 15.2 Proposed Tables

| Table | Description | Output file |
|-------|-------------|-------------|
| 1 | Sample construction | `s01_sample_construction.tex` |
| 2 | Summary statistics | `s02_summary_stats.tex` / `.csv` |
| 3 | Pre-treatment balance table | `s03_balance_table.tex` / `.csv` |
| 4 | Main event-study regression (3 specs) | `s04_regression_table.tex` / `.csv` |
| 5 | Binary vs. intensity-weighted regression | `s06_regression_intensity.tex` / `.csv` |
| 6 | Intensity quartile regression | `s06b_regression_intensity_quartiles.tex` / `.csv` |
| 7 | Insurance mechanism (policies + claims) | `s08_regression_insurance.tex` / `.csv` |
| 8 | Heterogeneity: up/down reclassification | `s09_regression_updown.tex` / `.csv` |
| 9 | Heterogeneity: disclosure interaction | `s09b_regression_disclosure.tex` / `.csv` |
| 10 | Heterogeneity: Republican interaction | `s09c_regression_republican.tex` / `.csv` |
| 11 | Robustness (weighted, unweighted, geo intensity) | `s095_robustness_table.tex` / `.csv` |
| A1 | SFHA-crossing subsample | `s09d_regression_sfha_crossing.tex` / `.csv` |
| A2 | Insurance by risk direction | `s08b_regression_insurance_updown.tex` / `.csv` |
| A3 | Simple TWFE DiD | `s07_did_twfe.tex` |
| A4 | Leave-one-out by state | `s15_leave_one_out_state.csv` |
| A5 | Alternative clustering coefficients | `s16_event_study_alt_clustering_coefficients.csv` |

## 15.3 Proposed Figures

| Figure | Description | Output file |
|--------|-------------|-------------|
| 1 | Treatment timing histogram | `s10_treatment_timing_hist.png` |
| 2 | Parallel trends (event-time pre-treatment coefficients) | `s10_parallel_trends.png` |
| 3 | Baseline event-study coefficients | `s05_event_study_main.png` / `.pdf` |
| 4 | Intensity-weighted event study | `s06_event_study_intensity.png` / `.pdf` |
| 5 | Intensity quartile event studies | `s06b_event_study_intensity_quartiles.png` / `.pdf` |
| 6 | Insurance policies event study | `s08_event_study_policies.png` / `.pdf` |
| 7 | Republican heterogeneity event study | `s09c_event_study_republican.png` / `.pdf` |
| A1 | Up/down reclassification event study | `s09_event_study_updown.png` / `.pdf` |
| A2 | Disclosure heterogeneity event study | `s09b_event_study_disclosure.png` / `.pdf` |
| A3 | Up/down insurance event study | `s08b_event_study_policies_updown.png` / `.pdf` |
| A4 | SFHA-crossing event study | `s09d_event_study_sfha_crossing.png` / `.pdf` |
| A5 | Bacon decomposition | `s12_bacon_decomposition.png` / `.pdf` |
| A6 | Callaway & Sant'Anna event study | `s13_event_study_cs.png` / `.pdf` |
| A7 | Placebo event study (unemployment) | `s14_event_study_placebo.png` / `.pdf` |

---

# 16. Writing Notes for the Final Paper

## 16.1 Tone

Write in journal style:

* precise,
* restrained,
* explicit about what is causal versus descriptive,
* interpret coefficients economically, not only statistically.

## 16.2 What to Emphasize

Emphasize:

* the baseline event study,
* the intensity result,
* the gradual timing,
* the distinction between strong and weak supporting evidence.

## 16.3 What to De-Emphasize

De-emphasize:

* the Republican interaction as a core claim,
* weak disclosure-law effects,
* any placebo that does not behave like a clean null.

## 16.4 Table Introductions

Every table should have a short paragraph before it stating:

* what the table contains,
* variable definitions,
* what the reader should look for,
* why the table matters.

This directly follows the paper guidance and will improve the write-up score.

---

# 17. References

Below is a working references section with URLs. In the final paper, format these consistently in your preferred citation style.

Abadie, Alberto. 2005. “Semiparametric Difference-in-Differences Estimators.” *Review of Economic Studies* 72(1): 1–19.
URL: [https://academic.oup.com/restud/article/72/1/1/1581053](https://academic.oup.com/restud/article/72/1/1/1581053)

Callaway, Brantly, and Pedro H. C. Sant’Anna. 2021. “Difference-in-Differences with Multiple Time Periods.” *Journal of Econometrics* 225(2): 200–230.
URL: [https://www.sciencedirect.com/science/article/pii/S0304407620303948](https://www.sciencedirect.com/science/article/pii/S0304407620303948)

Federal Emergency Management Agency (FEMA). “Letters of Map Revision (LOMRs).”
URL: [https://www.fema.gov/flood-maps/change-your-flood-zone/letters-map-revision](https://www.fema.gov/flood-maps/change-your-flood-zone/letters-map-revision)

Federal Emergency Management Agency (FEMA). “National Flood Insurance Program.”
URL: [https://www.fema.gov/flood-insurance](https://www.fema.gov/flood-insurance)

Federal Reserve Bank of St. Louis, FRED. “Consumer Price Index for All Urban Consumers (CPI-U).”
URL: [https://fred.stlouisfed.org/series/CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL)

Goodman-Bacon, Andrew. 2021. “Difference-in-Differences with Variation in Treatment Timing.” *Journal of Econometrics* 225(2): 254–277.
URL: [https://www.sciencedirect.com/science/article/pii/S0304407621001445](https://www.sciencedirect.com/science/article/pii/S0304407621001445)

Moulton, Brent R. 1990. “An Illustration of a Pitfall in Estimating the Effects of Aggregate Variables on Micro Units.” *Review of Economics and Statistics* 72(2): 334–338.
URL: [https://www.jstor.org/stable/2109724](https://www.jstor.org/stable/2109724)

Sant’Anna, Pedro H. C., and Jun Zhao. 2020. “Doubly Robust Difference-in-Differences Estimators.” *Journal of Econometrics* 219(1): 101–122.
URL: [https://www.sciencedirect.com/science/article/pii/S0304407620301901](https://www.sciencedirect.com/science/article/pii/S0304407620301901)

Sun, Liyang, and Sarah Abraham. 2021. “Estimating Dynamic Treatment Effects in Event Studies with Heterogeneous Treatment Effects.” *Journal of Econometrics* 225(2): 175–199.
URL: [https://www.sciencedirect.com/science/article/pii/S030440762030378X](https://www.sciencedirect.com/science/article/pii/S030440762030378X)

Zillow Research. “ZHVI User Guide / Home Value Data Documentation.”
URL: [https://www.zillow.com/research/data/](https://www.zillow.com/research/data/)

U.S. Census Bureau. “ZIP Code Tabulation Areas (ZCTAs).”
URL: [https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html](https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html)

