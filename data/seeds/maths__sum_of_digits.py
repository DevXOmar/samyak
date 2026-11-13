from __future__ import annotations
import math
def sum_of_digits(n: int) -> int:
    """
    Find the sum of digits of a number.
    >>> sum_of_digits(12345)
    15
    >>> sum_of_digits(123)
    6
    >>> sum_of_digits(-123)
    6
    >>> sum_of_digits(0)
    0
    """
    n = abs(n)
    res = 0
    while n > 0:
        res += n % 10
        n //= 10
    return res

def sum_of_digits_recursion(n: int) -> int:
    """
    Find the sum of digits of a number using recursion
    >>> sum_of_digits_recursion(12345)
    15
    >>> sum_of_digits_recursion(123)
    6
    >>> sum_of_digits_recursion(-123)
    6
    >>> sum_of_digits_recursion(0)
    0
    """
    n = abs(n)
    return n if n < 10 else n % 10 + sum_of_digits_recursion(n // 10)

def sum_of_digits_compact(n: int) -> int:
    """
    Find the sum of digits of a number
    >>> sum_of_digits_compact(12345)
    15
    >>> sum_of_digits_compact(123)
    6
    >>> sum_of_digits_compact(-123)
    6
    >>> sum_of_digits_compact(0)
    0
    """
    return sum(int(c) for c in str(abs(n)))
