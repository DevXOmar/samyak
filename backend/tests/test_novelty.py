from samyak.ml import ModelService, novelty_evidence, index_identity
from samyak.structure import analyze


def test_train_only_novelty_and_model_disagreement():
    source = "def rare_shape(text):\n    return {char: text.count(char) for char in text}\n"
    _, functions, _ = analyze(source)
    model = ModelService()
    model.predict(functions)
    evidence = novelty_evidence(model, functions, source, model.retrieve(source))
    assert evidence["basis"] == "HEURISTIC_NOT_CALIBRATED"
    assert 0 <= evidence["functions"][0]["disagreement"] <= 1
    assert evidence["index_id"] == index_identity(model.bundle)
    assert all(p["split"] == "train" for p in model.bundle["precedents"])
    assert "not" in evidence["reason"].lower() or evidence["abstain"]


def test_no_model_does_not_fabricate_novelty(tmp_path):
    assert novelty_evidence(ModelService(tmp_path), [], "x=1", [])["status"] == "NOT_SUPPORTED"
