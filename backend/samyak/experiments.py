"""Bounded experiments use exactly the existing execution and immutable-job contracts."""

from .precedent_experiment import compare_precedents
from .ledger_experiment import verify_ledger

HANDLERS = {"precedents": compare_precedents, "ledger": verify_ledger}


def run_experiment(action, report, payload, runner, stage):
    handler = HANDLERS.get(action)
    if handler is None:
        report.intelligence[action] = {
            "status": "NOT_SUPPORTED",
            "reason": "This experiment is not supported by this engine revision",
        }
        return
    handler(report, payload, runner, stage)
