import ast
from collections import Counter
import io
import json
import os
from pathlib import Path
import tokenize
import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.metrics.pairwise import cosine_similarity
from .structure import FEATURES, numeric
from .store import ROOT, digest


def code_text(source):
    """Ignore comments/docstrings; preserve code operators and API/identifier tokens."""
    try:
        tree = ast.parse(source)
        for n in ast.walk(tree):
            if (
                isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
                and n.body
                and isinstance(n.body[0], ast.Expr)
                and isinstance(n.body[0].value, ast.Constant)
                and isinstance(n.body[0].value.value, str)
            ):
                n.body = n.body[1:] or [ast.Pass()]
        source = ast.unparse(tree)
        tokens = []
        for t in tokenize.generate_tokens(io.StringIO(source).readline):
            if t.type in {
                tokenize.COMMENT,
                tokenize.ENCODING,
                tokenize.ENDMARKER,
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
            }:
                continue
            tokens.append(t.string)
        return " ".join(tokens)
    except (SyntaxError, tokenize.TokenError):
        return source


def values(source):
    fn = next((n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef)), None)
    features = numeric(fn) if fn else dict.fromkeys(FEATURES, 0)
    return [features[k] for k in FEATURES]


def matrix(vectorizer, sources):
    return hstack(
        [
            vectorizer.transform([code_text(s) for s in sources]),
            csr_matrix(np.array([values(s) for s in sources])),
        ],
        format="csr",
    )


class ModelService:
    def __init__(self, directory=None):
        directory = Path(directory or os.getenv("SAMYAK_MODELS", ROOT / "data/models"))
        if (directory / "CURRENT").exists():
            current = (directory / "CURRENT").read_text().strip()
            if len(current) == 64 and all(c in "0123456789abcdef" for c in current):
                directory = directory / "versions" / current
        self.bundle = None
        self.meta = {
            "status": "MODEL_UNAVAILABLE",
            "risk_interpretation": "Highest modeled function label risk",
            "calibration": "UNAVAILABLE",
        }
        if (directory / "model.joblib").exists():
            # Only trusted locally trained artifacts. Never deserialize uploaded model files.
            self.meta = json.loads((directory / "manifest.json").read_text())
            if digest((directory / "model.joblib").read_bytes()) != self.meta["artifact_sha256"]:
                raise ValueError("Model artifact integrity mismatch")
            self.bundle = joblib.load(directory / "model.joblib")

    def predict(self, functions):
        if self.bundle is None or not functions:
            return
        x = matrix(self.bundle["tfidf"], [f.source for f in functions])
        probs = self.bundle["risk"].predict_proba(x)[:, 1]
        dist = self.bundle["family"].predict_proba(x)
        for fn, risk, family in zip(functions, probs, dist):
            fn.risk = float(risk)
            fn.family_distribution = dict(zip(self.bundle["families"], map(float, family)))
            best = max(fn.family_distribution, key=fn.family_distribution.get)
            fn.family = best if max(family) >= 0.4 else "UNKNOWN_FAMILY"

    def retrieve(self, source, k=3):
        if self.bundle is None or not self.bundle["precedents"]:
            return []
        query = self.bundle["tfidf"].transform([code_text(source)])
        sims = cosine_similarity(query, self.bundle["precedent_vectors"])[0]
        result = []
        normalized = code_text(source)
        for index in np.argsort(sims)[::-1]:
            row = self.bundle["precedents"][index]
            # Exact/self matches must not reveal an answer.
            if normalized == code_text(row["buggy"]):
                continue
            result.append(
                {
                    "id": row["id"],
                    "similarity": float(sims[index]),
                    "family": row["family"],
                    "operator": row["operator"],
                    "split": row["split"],
                    "domain": row["domain"],
                    "origin": row.get("origin"),
                    "license_path": row.get("license_path", "data/seeds/THEALGORITHMS_LICENSE.md"),
                    "edit_summary": row["operator"],
                    "diff": row["diff"][:2000],
                }
            )
            if len(result) >= k:
                break
        return result


def edit_priors(precedents, operators):
    frequencies = Counter()
    for p in precedents:
        if p["operator"] in operators:
            frequencies[p["operator"]] += p["similarity"]
    total = sum(frequencies.values()) + 0.5 * len(operators)
    return {op: (0.5 + frequencies[op]) / total if total else 0 for op in operators}


def index_identity(bundle):
    return digest(
        json.dumps(
            [
                {
                    "id": p["id"],
                    "buggy": digest(p["buggy"]),
                    "fixed": digest(p["fixed"]),
                    "operator": p["operator"],
                }
                for p in bundle["precedents"]
            ],
            sort_keys=True,
        )
    )


def novelty_evidence(model, functions, source, precedents):
    """Heuristic novelty from train-only reference features and independent model disagreement."""
    if model.bundle is None or not functions:
        return {
            "status": "NOT_SUPPORTED",
            "reason": "Trained model or supported functions unavailable",
            "abstain": True,
        }
    bundle = model.bundle
    training = np.array([values(p[k]) for p in bundle["precedents"] for k in ("buggy", "fixed")])
    low, high = np.quantile(training, [0.05, 0.95], axis=0)
    x = matrix(bundle["tfidf"], [f.source for f in functions])
    rf = bundle["rf"].predict_proba(x)[:, 1]
    xgb = bundle["risk"].predict_proba(x)[:, 1]
    known_ast = {type(n).__name__ for p in bundle["precedents"] for n in ast.walk(ast.parse(p["buggy"]))}
    unfamiliar_ast = sorted({type(n).__name__ for n in ast.walk(ast.parse(source))} - known_ast)
    rows = []
    for fn, baseline, operational in zip(functions, rf, xgb):
        vector = np.array(values(fn.source))
        outside = [FEATURES[i] for i in range(len(FEATURES)) if vector[i] < low[i] or vector[i] > high[i]]
        rows.append(
            {
                "function": fn.name,
                "rf_risk": float(baseline),
                "xgb_risk": float(operational),
                "disagreement": float(abs(baseline - operational)),
                "outlier_features": outside,
                "outlier_fraction": len(outside) / len(FEATURES),
            }
        )
    similarity = max((p["similarity"] for p in precedents), default=0)
    abstain = (
        similarity < 0.15
        or any(r["disagreement"] > 0.35 or r["outlier_fraction"] > 0.35 for r in rows)
        or bool(unfamiliar_ast)
    )
    return {
        "status": "UNFAMILIAR" if abstain else "HISTORICAL_NEIGHBORHOOD",
        "abstain": abstain,
        "basis": "HEURISTIC_NOT_CALIBRATED",
        "nearest_similarity": similarity,
        "functions": rows,
        "unseen_ast_types": unfamiliar_ast,
        "thresholds": {"similarity_min": 0.15, "disagreement_max": 0.35, "outlier_fraction_max": 0.35},
        "feature_reference": "Train-only 5th/95th numeric AST percentiles",
        "index_id": index_identity(bundle),
        "reason": "Lower-trust ML/family conclusion; static and runtime checks continue"
        if abstain
        else "Historical familiarity is not a correctness oracle",
    }
