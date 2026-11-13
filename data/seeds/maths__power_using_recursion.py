from __future__ import annotations
import math
def power(base: int, exponent: int) -> float:
    """
    Calculate the power of a base raised to an exponent.

    >>> power(3, 4)
    81
    >>> power(2, 0)
    1
    >>> all(power(base, exponent) == pow(base, exponent)
    ...     for base in range(-10, 10) for exponent in range(10))
    True
    >>> power('a', 1)
    'a'
    >>> power('a', 2)
    Traceback (most recent call last):
        ...
    TypeError: can't multiply sequence by non-int of type 'str'
    >>> power('a', 'b')
    Traceback (most recent call last):
        ...
    TypeError: unsupported operand type(s) for -: 'str' and 'int'
    >>> power(2, -1)
    Traceback (most recent call last):
        ...
    RecursionError: maximum recursion depth exceeded
    >>> power(0, 0)
    1
    >>> power(0, 1)
    0
    >>> power(5,6)
    15625
    >>> power(23, 12)
    21914624432020321
    """
    return base * power(base, (exponent - 1)) if exponent else 1
