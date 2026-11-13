from __future__ import annotations
import math
def num_digits(n: int) -> int:
    """
    Find the number of digits in a number.

    >>> num_digits(12345)
    5
    >>> num_digits(123)
    3
    >>> num_digits(0)
    1
    >>> num_digits(-1)
    1
    >>> num_digits(-123456)
    6
    >>> num_digits('123')  # Raises a TypeError for non-integer input
    Traceback (most recent call last):
        ...
    TypeError: Input must be an integer
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")

    digits = 0
    n = abs(n)
    while True:
        n = n // 10
        digits += 1
        if n == 0:
            break
    return digits

def num_digits_fast(n: int) -> int:
    """
    Find the number of digits in a number.
    abs() is used as logarithm for negative numbers is not defined.

    >>> num_digits_fast(12345)
    5
    >>> num_digits_fast(123)
    3
    >>> num_digits_fast(1000)
    4
    >>> num_digits_fast(10**15)
    16
    >>> num_digits_fast(0)
    1
    >>> num_digits_fast(-1)
    1
    >>> num_digits_fast(-123456)
    6
    >>> num_digits_fast('123')  # Raises a TypeError for non-integer input
    Traceback (most recent call last):
        ...
    TypeError: Input must be an integer
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    return 1 if n == 0 else math.floor(math.log10(abs(n)) + 1)

def num_digits_faster(n: int) -> int:
    """
    Find the number of digits in a number.
    abs() is used for negative numbers.

    >>> num_digits_faster(12345)
    5
    >>> num_digits_faster(123)
    3
    >>> num_digits_faster(0)
    1
    >>> num_digits_faster(-1)
    1
    >>> num_digits_faster(-123456)
    6
    >>> num_digits_faster('123')  # Raises a TypeError for non-integer input
    Traceback (most recent call last):
        ...
    TypeError: Input must be an integer
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")

    return len(str(abs(n)))
