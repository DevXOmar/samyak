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
    if name == "inventory_planner":
        tests += _authored(_inventory_cases(), "FIXTURE_INVENTORY_CONTRACT")
    if name == "ledger_reconciler":
        tests += _authored(_ledger_cases(), "FIXTURE_LEDGER_CONTRACT")
    return {"source": source, "tests": [t.model_dump() for t in tests], "fixture": name}


def _authored(cases, origin):
    return [
        TestCase(
            function=fn,
            args=args,
            expected=expected,
            has_expected=True,
            tier="A",
            domain="CONFIRMED",
            origin=origin,
            reason=reason,
        )
        for fn, args, expected, reason in cases
    ]


def _inventory_cases():
    """Correct planner: every authored oracle passes, so no candidate may claim a fix.

    Expected values come from independent references (linear scans, sorted()) or
    hand-computed planning arithmetic; the fixture never reads the program's output.
    """
    cases = []
    for levels, threshold in [([], 5), ([3], 3), ([3], 4), ([1, 3, 3, 5], 3), ([1, 3, 5], 6), ([1, 3, 5], 0)]:
        expected = next((i for i, v in enumerate(levels) if v >= threshold), len(levels))
        cases.append(
            (
                "first_at_least",
                [levels, threshold],
                expected,
                "Lower bound: first index >= threshold, else len",
            )
        )
    for values in ([5, 2, 2, 9, 1], [], [3, -1, 3]):
        cases.append(("insertion_sort", [values], sorted(values), "Ascending sort preserving multiplicities"))
    for first, second in [([2, 5, 9], [1, 5, 7, 12]), ([], [4]), ([3, 8], [])]:
        cases.append(
            ("merge_receipts", [first, second], sorted(first + second), "Merge keeps every receipt in order")
        )
    sku_reason = "Sentinel contract: None means not stocked; position 0 is valid and callers depend on it"
    cases += [
        ("median_level", [[4, 1, 3, 2]], 2.5, "Even-length median averages the two middle levels"),
        ("median_level", [[]], 0.0, "Empty history has median 0.0 by planning convention"),
        ("moving_average", [[10, 20, 30, 40], 2], [15.0, 25.0, 35.0], "Trailing two-day averages"),
        ("reorder_quantity", [30, 12, 4, 2], 42, "12/day x (4 lead + 2 safety) = 72 point, 30 on hand"),
        ("classify_level", [0, 72, 150], "STOCKOUT", "No stock on the shelf"),
        ("classify_level", [72, 72, 150], "REORDER", "At the reorder point"),
        ("classify_level", [151, 72, 150], "OVERSTOCK", "Above shelf capacity"),
        ("find_sku", [[1001, 1004, 1009], 1001], 0, sku_reason),
        ("find_sku", [[1001, 1004, 1009], 1005], None, sku_reason),
        ("has_sku", [[1001, 1004, 1009], 1001], True, sku_reason),
        ("has_sku", [[1001, 1004, 1009], 1005], False, sku_reason),
    ]
    return cases


def _ledger_cases():
    """Buggy reconciler. Answer key (not revealed in the source):

    1. count_settled_by uses `< cutoff`; the docstring says "at or before" (fixable: < -> <=).
       Authored oracles below fail on the original and validate the boundary repair.
    2. find_account is correct; replacing its None sentinel breaks is_known_account (caller trap).
    3. average_ticket guards `is None` instead of emptiness -> ZeroDivisionError on [].
    4. running_balance iterates range(1, len - 1) and drops the final delta.
    5. settlement_fee leaves fee None for unknown methods -> TypeError.
    6. late_fee charges every late day instead of only the days beyond the grace period.
    7. has_duplicate_payment compares payment_ids[i] with itself (should be [j]).
    8. tag_batch keeps a mutable default, so tags leak across reconciliation runs.
    9. merge_statements forgets to append the tail of the second feed.
    10. interest_accrued truncates to whole cents per day before multiplying by days.
    11. chargeback_ratio_bps guards the numerator instead of the zero denominator.

    Only (1) and the caller contract carry authored oracles, so one repair can validate;
    the others surface as static findings, runtime witnesses or Contract Studio work.
    """
    cases = []
    for timestamps, cutoff in [
        ([540, 600, 615, 660, 720], 660),
        ([5], 5),
        ([], 10),
        ([5], 4),
        ([1, 2, 3], 9),
    ]:
        expected = sum(1 for t in timestamps if t <= cutoff)
        cases.append(
            ("count_settled_by", [timestamps, cutoff], expected, "Inclusive cutoff: settled at or before")
        )
    account_reason = "Sentinel contract: None means unknown account; callers depend on it"
    cases += [
        ("find_account", [[3101, 3107, 3112], 3101], 0, account_reason),
        ("find_account", [[3101, 3107, 3112], 3112], 2, account_reason),
        ("find_account", [[3101, 3107, 3112], 3110], None, account_reason),
        ("is_known_account", [[3101, 3107, 3112], 3107], True, account_reason),
        ("is_known_account", [[3101, 3107, 3112], 3110], False, account_reason),
        ("is_known_account", [[], 3101], False, account_reason),
    ]
    return cases
