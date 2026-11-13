import json
from pathlib import Path
import joblib
from samyak.ml import code_text
from samyak.store import digest
from scripts.data_sources import partition

ROOT = Path(__file__).resolve().parents[2]


def test_source_partition_precedes_mutation():
    source = json.loads((ROOT / "data/source_manifest.json").read_text())
    for seed in source["seeds"]:
        assert seed["split"] == partition("algorithm:" + seed["id"])
    assert all("quixbugs" not in s["name"].lower() for s in source["sources"])


def test_lineage_and_content_disjoint_and_witnessed():
    corpus = json.loads((ROOT / "data/corpus.json").read_text())
    groups, hashes = {}, {}
    for pair in corpus["pairs"]:
        assert "quixbugs" not in json.dumps(pair).lower()
        groups.setdefault(pair["group"], set()).add(pair["split"])
        for key in ("buggy", "fixed"):
            hashes.setdefault(digest(code_text(pair[key])), set()).add(pair["split"])
        if pair["domain"] == "SYNTHETIC_ALGORITHM":
            assert pair["confidence"] == "SANDBOX_DISTINGUISHING_WITNESS"
            assert pair["witnesses"]
    assert all(len(splits) == 1 for splits in groups.values())
    assert all(len(splits) == 1 for splits in hashes.values())


def test_train_only_tfidf_and_precedents():
    bundle = joblib.load(ROOT / "data/models/model.joblib")
    manifest = json.loads((ROOT / "data/models/manifest.json").read_text())
    assert manifest["tfidf_fit_split"] == "train"
    assert all(p["split"] == "train" for p in bundle["precedents"])
    corpus = json.loads((ROOT / "data/corpus.json").read_text())
    train_text = " ".join(
        code_text(p[k]) for p in corpus["pairs"] if p["split"] == "train" for k in ("buggy", "fixed")
    )
    analyzer = bundle["tfidf"].build_analyzer()
    assert set(bundle["tfidf"].vocabulary_) <= set(analyzer(train_text))
    assert manifest["artifact_sha256"] == digest((ROOT / "data/models/model.joblib").read_bytes())
    assert manifest["metrics"]["test"]["REAL_BUGSINPY"]["xgb"]["n"] > 0
