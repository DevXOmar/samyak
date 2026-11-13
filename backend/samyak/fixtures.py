from .store import ROOT
from .contracts import TestCase


def fixture(name):
    source = (ROOT / "fixtures" / f"{name}.py").read_text()
    tests = []
    if name == "binary_search":
        # Trusted, independently authored linear reference; never reads original output.
        for nums, target in [
            ([], 0),
            ([7], 7),
            ([1, 3, 5], 5),
            ([1, 3, 5], 1),
            ([1, 3, 5], 9),
            ([1, 3, 5], 3),
        ]:
            expected = next((i for i, value in enumerate(nums) if value == target), -1)
            tests.append(
                TestCase(
                    function=name,
                    args=[nums, target],
                    expected=expected,
                    has_expected=True,
                    tier="A",
                    domain="CONFIRMED",
                    origin="FIXTURE_TRUSTED_LINEAR_REFERENCE",
                    reason="Authored search contract: sorted unique ints; first matching index, otherwise -1",
                )
            )
    if name == "caller_regression":
        for fn, args, expected in [
            ("lookup", [[7], 7], 0),
            ("lookup", [[1, 3, 5], 3], 1),
            ("contains", [[7], 7], True),
            ("contains", [[1, 3, 5], 9], False),
            ("contains", [[], 9], False),
            ("lookup", [[], 9], None),
        ]:
            tests.append(
                TestCase(
                    function=fn,
                    args=args,
                    expected=expected,
                    has_expected=True,
                    tier="A",
                    domain="CONFIRMED",
                    origin="FIXTURE_CALLER_CONTRACT",
                    reason="Authored sentinel contract: None means missing; callers depend on it",
                )
            )
    return {"source": source, "tests": [t.model_dump() for t in tests], "fixture": name}
