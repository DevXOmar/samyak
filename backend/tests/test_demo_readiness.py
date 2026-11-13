import httpx
import pytest
from scripts.phase2_demo import main


def test_demo_connection_failure_is_actionable(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx.Client, "get", fail)
    with pytest.raises(SystemExit, match="make dev"):
        main()


@pytest.mark.parametrize(
    "worker,runner,model,instruction",
    [
        ("OFFLINE", "AVAILABLE", "TRAINED", "make dev"),
        ("READY", "EXECUTION_UNAVAILABLE", "TRAINED", "make runner"),
        ("READY", "AVAILABLE", "MODEL_UNAVAILABLE", "make train"),
    ],
)
def test_demo_readiness_instructions(monkeypatch, worker, runner, model, instruction):
    monkeypatch.setattr(
        httpx.Client,
        "get",
        lambda *args, **kwargs: httpx.Response(
            200,
            request=httpx.Request("GET", "http://localhost/v1/capabilities"),
            json={"worker": worker, "runner": {"status": runner}, "model_status": model},
        ),
    )
    with pytest.raises(SystemExit, match=instruction):
        main()
