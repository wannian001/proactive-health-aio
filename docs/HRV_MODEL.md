# Personal trained HRV model

A local next-calendar-day forecast of the owner's recorded daily HRV in milliseconds.
It does not infer energy, soreness, tissue healing or a clinical recovery score. No coursework
participant records are pooled into the owner's model. Runtime inference uses only Python's
standard library; explicit training requires numpy and scikit-learn.

## Data and target

Read the configured AIO `body_daily.csv`. Exclude today, future rows and explicitly partial days.
A pair needs HRV on calendar day D and D+1, plus at least ten observed HRV days in D's 28-day window.
Missing days are not compressed together; the next observed day is not necessarily tomorrow.
Target is `log(HRV[D+1] / median_28[D])`, transformed back to ms. All feature windows end at D.

The HRV-only feature set contains current/lagged HRV, 3/7-day means, 7/90-day medians, 28-day
variability and coverage, baseline level and recent slope. An alternative adds prior observed
sleep, resting heart rate, steps, exercise and training. Future-night sleep is never a feature.
Unknown values use the training fold's medians, with missing-value flags. The normalization and
imputation are fitted separately within every training fold.

## Selection and evaluation

- Three baselines: 28-day median, 7-day mean, and last HRV value.
- Twelve trained candidates: HRV-only / context × Ridge alpha 1/10/100 × recency half-life 365/730 days.
- Three expanding calendar validation folds, each 90 days. Choose on weighted aggregate validation MAE.
- The following 90-day block calibrates an empirical 80th-percentile absolute-error range.
- The last 180 calendar days are held out for this run; only eligible complete pairs are evaluated.
  Fit on pre-test data once, then predict test days using only the features available at each anchor.
  No test result is used to retune parameters or choose a candidate.
- Report MAE against the median baseline, per-month errors, sample count and interval coverage.
  An exploratory paired bootstrap resamples non-overlapping calendar-week blocks (2,000 draws,
  fixed seed) for the error difference. A range crossing zero does not establish a stable advantage.
- After evaluation, refit the chosen specification on all eligible historical pairs for future use.
  Export both the selected fit and best learned fit. If a simple baseline wins validation, it stays active.
- Export checks every fitted-row prediction against scikit-learn, including inverse normalization;
  discrepancy above 1e-7 ms refuses export. JSON contains coefficients, preprocessing parameters,
  training-input fingerprint, selection results and the genuinely held-out comparison cases.

The reference interval is not a guaranteed personal probability interval: observations are time dependent,
measurement conditions vary, and missingness may be informative. Historical performance is not prospective
validation. Final model refitting can change error behavior. No causal attribution is made from coefficients.

## Local use

```sh
# First inspect eligibility without writing a model.
<python-with-sklearn> -B -m healthaio.hrv_train --config <private-profile>/healthaio.json --as-of YYYY-MM-DD
# Explicit training and installation into the same private profile.
<python-with-sklearn> -B -m healthaio.hrv_train --config <private-profile>/healthaio.json --as-of YYYY-MM-DD --apply
```

`hrv_model.json` sits next to the private profile config, outside the source worktree. The writer validates
and atomically replaces it under the existing profile lock, with mode 0600. It never modifies source
health tables or subjective diaries. The CLI rechecks the training input fingerprint before installing.
No background training, scheduler, automatic source sync or public deployment is created.

`GET /api/recovery` includes `hrv_prediction`. The card shows the last complete HRV, its following-day
estimate and range, the last sixty held-out cases, model training date and measured error. Old device
data remain explicitly dated: an estimate whose target date has already passed is a historical-data
estimate, not today's prediction. A backdated view does not run future-trained coefficients. Old training
inputs revised in place trigger a retraining message; appended dates can be predicted without retraining.
Missing/corrupt models or invalid source rows fail explicitly without breaking the rest of Recovery.

The new model leaves the original energy and regional soreness diaries/forecasts separate. New complete
rows in this AIO profile update inference on refresh; continuous syncing from a separate personal system
must be configured separately. A model older than 45 days displays a retraining reminder.

## Verification

- `tests/test_hrv_model.py`: future-data isolation, calendar gaps/partial days, source revisions,
  invalid model handling, historical-date guard, arithmetic and bilingual rendering.
- `tests/test_hrv_training.py` (optional training environment): altering every held-out label must leave
  candidate selection and calibration unchanged; portable inference parity is checked.
- Real training statistics and evaluation cases remain in the private model/report, not in this repository.

Implementation references: [scikit-learn time-series forecasting example](https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html)
and [cross-validation documentation](https://scikit-learn.org/stable/modules/cross_validation.html).
The installed training environment was verified separately; the application has no new runtime dependency.
