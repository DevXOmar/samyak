# SAMYAK Phase 1 model card

Two independent tasks: binary reported/synthetic defect risk and multiclass defect family; RF baseline and XGBoost heads. TF-IDF and AST features.

Model ID: `d096c67306a7cbf78e99cf6ba5868d60e7ca4cf1e3546273e17fa5417ed6c48f`. Calibration: UNCALIBRATED_INSUFFICIENT_COHORT.

- Fixed revisions mean patched reported bug, not globally clean code
- Small bounded corpus; no generalization claim
- Mutation witnesses demonstrate differences, not universal parent correctness
- Hyperparameters fixed in advance; no test-driven selection

See manifest.json for exact grouped cohorts, counts and metrics.json for measured confusion matrices and localization ablation. No QuixBugs exposure. Retrieval contains train pairs only. Low similarity does not prove a defect. Family classes with fewer than four training rows are omitted.
