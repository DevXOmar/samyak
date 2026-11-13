# SAMYAK Phase 1 model card

Two independent tasks: binary reported/synthetic defect risk and multiclass defect family; RF baseline and XGBoost heads. TF-IDF and AST features.

Model ID: `6ac7f0d34540581327a9dceb887b8b58b3e4d726d95fa9cfa18026acfdb94a04`. Calibration: SIGMOID_DISJOINT_CALIBRATION.

- Fixed revisions mean patched reported bug, not globally clean code
- Small bounded corpus; no generalization claim
- Mutation witnesses demonstrate differences, not universal parent correctness
- Hyperparameters fixed in advance; no test-driven selection

See manifest.json for exact grouped cohorts, counts and metrics.json for measured confusion matrices and localization ablation. No QuixBugs exposure. Retrieval contains train pairs only. Low similarity does not prove a defect. Family classes with fewer than four training rows are omitted.
