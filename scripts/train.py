"""Reproducible training/evaluation; source parsing only, no source execution."""

from collections import Counter
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    precision_recall_fscore_support,
    confusion_matrix,
    brier_score_loss,
    classification_report,
)
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from samyak.ml import code_text, matrix
from samyak.structure import analyze, localize
from samyak.store import digest

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261113


def rows_for(pairs, split):
    rows, seen = [], set()
    for pair in pairs:
        if pair["split"] != split:
            continue
        for key, risk in [("buggy", 1), ("fixed", 0)]:
            source = pair[key]
            signature = digest(code_text(source))
            if signature in seen:
                continue
            seen.add(signature)
            rows.append(
                {
                    "source": source,
                    "risk": risk,
                    "family": pair["family"] if risk else "CLEAN",
                    "domain": pair["domain"],
                    "group": pair["group"],
                }
            )
    return rows


def binary_metrics(y, p):
    labels = (p >= 0.5).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y, labels, average="binary", zero_division=0)
    both = len(set(y)) == 2
    return {
        "n": len(y),
        "positive_prevalence": float(np.mean(y)),
        "pr_auc": float(average_precision_score(y, p)) if both else None,
        "roc_auc": float(roc_auc_score(y, p)) if both else None,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "brier": float(brier_score_loss(y, p)),
        "confusion_matrix": confusion_matrix(y, labels, labels=[0, 1]).tolist(),
    }


def main():
    corpus_raw = (ROOT / "data/corpus.json").read_bytes()
    corpus = json.loads(corpus_raw)
    pairs = corpus["pairs"]
    rows = {split: rows_for(pairs, split) for split in ["train", "validation", "calibration", "test"]}
    if len(rows["train"]) < 10 or not rows["test"]:
        raise SystemExit("Insufficient verified data; run data_sources and build_corpus with Docker")
    # Assert disjoint groups and token-normalized contents before fitting anything.
    for a in rows:
        for b in rows:
            if a >= b:
                continue
            assert not {r["group"] for r in rows[a]} & {r["group"] for r in rows[b]}
            assert not {digest(code_text(r["source"])) for r in rows[a]} & {
                digest(code_text(r["source"])) for r in rows[b]
            }
    tfidf = TfidfVectorizer(
        token_pattern=r"(?u)\b\w+\b|[<>!=+*/%-]+", ngram_range=(1, 2), max_features=1800, sublinear_tf=True
    )
    tfidf.fit([code_text(r["source"]) for r in rows["train"]])
    x = matrix(tfidf, [r["source"] for r in rows["train"]])
    y = np.array([r["risk"] for r in rows["train"]])
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=9,
        min_samples_leaf=2,
        random_state=SEED,
        n_jobs=1,
        class_weight="balanced",
    )
    xgb = XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.08,
        subsample=1,
        colsample_bytree=1,
        random_state=SEED,
        n_jobs=1,
        eval_metric="logloss",
    )
    rf.fit(x, y)
    xgb.fit(x, y)
    calibration = "UNCALIBRATED_INSUFFICIENT_COHORT"
    risk = xgb
    cal = rows["calibration"]
    if len(cal) >= 10 and len({r["risk"] for r in cal}) == 2:
        risk = CalibratedClassifierCV(FrozenEstimator(xgb), method="sigmoid")
        risk.fit(matrix(tfidf, [r["source"] for r in cal]), [r["risk"] for r in cal])
        calibration = "SIGMOID_DISJOINT_CALIBRATION"
    counts = Counter(r["family"] for r in rows["train"])
    eligible = {family for family, count in counts.items() if count >= 4}
    family_rows = [r for r in rows["train"] if r["family"] in eligible]
    encoder = LabelEncoder().fit([r["family"] for r in family_rows])
    fx = matrix(tfidf, [r["source"] for r in family_rows])
    fy = encoder.transform([r["family"] for r in family_rows])
    family = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.08, random_state=SEED, n_jobs=1)
    family_rf = RandomForestClassifier(
        n_estimators=100, max_depth=9, random_state=SEED, n_jobs=1, class_weight="balanced"
    )
    family.fit(fx, fy)
    family_rf.fit(fx, fy)
    metrics = {}
    for split in ["validation", "test"]:
        metrics[split] = {}
        for domain in ["REAL_BUGSINPY", "SYNTHETIC_ALGORITHM"]:
            cohort = [r for r in rows[split] if r["domain"] == domain]
            if not cohort:
                metrics[split][domain] = {"n": 0, "status": "UNAVAILABLE_NO_SAMPLES"}
                continue
            xx = matrix(tfidf, [r["source"] for r in cohort])
            yy = [r["risk"] for r in cohort]
            data = {
                "rf": binary_metrics(yy, rf.predict_proba(xx)[:, 1]),
                "xgb": binary_metrics(yy, risk.predict_proba(xx)[:, 1]),
            }
            supported = [r for r in cohort if r["family"] in eligible]
            if supported:
                fxx = matrix(tfidf, [r["source"] for r in supported])
                truth = encoder.transform([r["family"] for r in supported])
                for label, head in [("xgb_family", family), ("rf_family", family_rf)]:
                    pred = head.predict(fxx)
                    data[label] = {
                        "report": classification_report(
                            truth,
                            pred,
                            labels=list(range(len(encoder.classes_))),
                            target_names=list(encoder.classes_),
                            zero_division=0,
                            output_dict=True,
                        ),
                        "confusion_matrix": confusion_matrix(
                            truth, pred, labels=list(range(len(encoder.classes_)))
                        ).tolist(),
                        "abstain_rate": float(np.mean(head.predict_proba(fxx).max(axis=1) < 0.4)),
                        "excluded_unsupported": len(cohort) - len(supported),
                    }
            metrics[split][domain] = data
    precedents = [p for p in pairs if p["split"] == "train"]
    bundle = {
        "tfidf": tfidf,
        "risk": risk,
        "rf": rf,
        "xgb": xgb,
        "family": family,
        "family_rf": family_rf,
        "families": list(encoder.classes_),
        "precedents": precedents,
        "precedent_vectors": tfidf.transform([code_text(p["buggy"]) for p in precedents]),
    }
    ablation = {}
    for domain in ["REAL_BUGSINPY", "SYNTHETIC_ALGORITHM"]:
        cohort = [p for p in pairs if p["split"] == "test" and p["domain"] == domain and p["fault_lines"]]
        scores = {"RULES_GRAPH": [], "BINARY_ML": [], "BINARY_FAMILY_ML": []}
        for p in cohort:
            try:
                structure, functions, findings = analyze(p["buggy"])
                xx = matrix(tfidf, [f.source for f in functions])
                risks = risk.predict_proba(xx)[:, 1]
                families = family.predict_proba(xx)
                for fn, pr, fd in zip(functions, risks, families):
                    fn.risk = float(pr)
                    fn.family_distribution = dict(zip(encoder.classes_, map(float, fd)))
                for name, use_ml, use_family in [
                    ("RULES_GRAPH", False, False),
                    ("BINARY_ML", True, False),
                    ("BINARY_FAMILY_ML", True, True),
                ]:
                    ranking = localize(structure, functions, findings, ml=use_ml, family=use_family)
                    rank = next((i + 1 for i, r in enumerate(ranking) if r["line"] in p["fault_lines"]), None)
                    scores[name].append(rank)
            except (SyntaxError, ValueError):
                continue
        ablation[domain] = {
            name: {
                "n": len(ranks),
                "top1": sum(r == 1 for r in ranks) / len(ranks) if ranks else None,
                "top3": sum(r is not None and r <= 3 for r in ranks) / len(ranks) if ranks else None,
                "mrr": sum(1 / r if r else 0 for r in ranks) / len(ranks) if ranks else None,
            }
            for name, ranks in scores.items()
        }
    metrics["localization_ablation"] = ablation
    metrics["EXTERNAL_QUIXBUGS"] = {
        "status": "NOT_EVALUATED",
        "reason": "Phase 1 has no downloaded external cohort; zero training/retrieval/tuning exposure",
    }
    metrics["FAMILY_HOLDOUT"] = {
        "status": "NOT_EVALUATED",
        "reason": "No extra family holdout fitted; project/problem holdouts reported separately",
    }
    manifest = {
        "status": "TRAINED",
        "model_id": digest(
            corpus_raw
            + b"rf-xgb-tfidf-ast-v2"
            + (ROOT / "backend/samyak/structure.py").read_bytes()
            + Path(__file__).read_bytes()
        ),
        "seed": SEED,
        "corpus_hash": digest(corpus_raw),
        "calibration": calibration,
        "families": list(encoder.classes_),
        "family_train_counts": dict(counts),
        "domains": sorted({p["domain"] for p in pairs}),
        "cohorts": {
            s: {"rows": len(rr), "groups": sorted({r["group"] for r in rr})} for s, rr in rows.items()
        },
        "precedent_count": len(precedents),
        "tfidf_fit_split": "train",
        "metrics": metrics,
        "novelty_threshold": 0.15,
        "novelty_policy": "Fixed conservative unfamiliarity heuristic, not a calibrated novelty classifier",
        "risk_interpretation": "Highest modeled function training-label risk, not unconditional crash probability",
        "limitations": [
            "Fixed revisions mean patched reported bug, not globally clean code",
            "Small bounded corpus; no generalization claim",
            "Mutation witnesses demonstrate differences, not universal parent correctness",
            "Hyperparameters fixed in advance; no test-driven selection",
        ],
    }
    directory = ROOT / "data/models"
    directory.mkdir(exist_ok=True)
    # sklearn caches a process-specific id(stop_words); it is not learned state.
    tfidf.__dict__.pop("_stop_words_id", None)
    # Zero structured-array padding so sklearn tree pickles cannot capture allocator bytes.
    for forest in (rf, family_rf):
        for estimator in forest.estimators_:
            state = estimator.tree_.__getstate__()
            clean_nodes = np.zeros(state["nodes"].shape, dtype=state["nodes"].dtype)
            for field in state["nodes"].dtype.names:
                clean_nodes[field] = state["nodes"][field]
            state["nodes"] = clean_nodes
            estimator.tree_.__setstate__(state)
    joblib.dump(bundle, directory / "model.joblib", compress=3)
    manifest["artifact_sha256"] = digest((directory / "model.joblib").read_bytes())
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (directory / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (directory / "MODEL_CARD.md").write_text(
        "# SAMYAK Phase 1 model card\n\nTwo independent tasks: binary reported/synthetic defect risk and multiclass defect family; RF baseline and XGBoost heads. TF-IDF and AST features.\n\n"
        + f"Model ID: `{manifest['model_id']}`. Calibration: {calibration}.\n\n"
        + "\n".join("- " + line for line in manifest["limitations"])
        + "\n\nSee manifest.json for exact grouped cohorts, counts and metrics.json for measured confusion matrices and localization ablation. No QuixBugs exposure. Retrieval contains train pairs only. Low similarity does not prove a defect. Family classes with fewer than four training rows are omitted.\n"
    )
    # Publish an immutable model revision before changing the local serving pointer.
    import shutil

    version_dir = directory / "versions" / manifest["model_id"]
    version_dir.mkdir(parents=True, exist_ok=True)
    for name in ["model.joblib", "manifest.json", "metrics.json", "MODEL_CARD.md"]:
        target = version_dir / name
        if target.exists() and target.read_bytes() != (directory / name).read_bytes():
            raise RuntimeError("Model revision collision: existing immutable artifact differs")
        shutil.copyfile(directory / name, target)
    pointer = directory / "CURRENT.tmp"
    pointer.write_text(manifest["model_id"] + "\n")
    pointer.replace(directory / "CURRENT")
    print(
        json.dumps(
            {"model_id": manifest["model_id"], "cohorts": manifest["cohorts"], "ablation": ablation}, indent=2
        )
    )


if __name__ == "__main__":
    main()
