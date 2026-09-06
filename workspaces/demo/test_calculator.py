import pytest
from calculator import add, subtract, multiply, divide


def test_add_positive_integers():
    assert add(2, 3) == 5


def test_add_negative_integers():
    assert add(-2, -3) == -5


def test_add_mixed_integers():
    assert add(-2, 3) == 1


def test_add_floats():
    assert add(2.5, 3.1) == pytest.approx(5.6)


def test_add_zero():
    assert add(0, 5) == 5
    assert add(5, 0) == 5


def test_subtract_positive_integers():
    assert subtract(5, 3) == 2


def test_subtract_negative_integers():
    assert subtract(-5, -3) == -2


def test_subtract_mixed_integers():
    assert subtract(-5, 3) == -8


def test_subtract_floats():
    assert subtract(5.5, 2.2) == pytest.approx(3.3)


def test_subtract_zero():
    assert subtract(0, 5) == -5
    assert subtract(5, 0) == 5


def test_multiply_positive_integers():
    assert multiply(3, 4) == 12


def test_multiply_negative_integers():
    assert multiply(-3, -4) == 12


def test_multiply_mixed_integers():
    assert multiply(-3, 4) == -12


def test_multiply_floats():
    assert multiply(2.5, 4.0) == pytest.approx(10.0)


def test_multiply_by_zero():
    assert multiply(0, 5) == 0
    assert multiply(5, 0) == 0


def test_divide_positive_integers():
    assert divide(8, 2) == 4


def test_divide_negative_integers():
    assert divide(-8, -2) == 4


def test_divide_mixed_integers():
    assert divide(-8, 2) == -4


def test_divide_floats():
    assert divide(7.5, 2.5) == pytest.approx(3.0)


def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        divide(5, 0)
    with pytest.raises(ZeroDivisionError):
        divide(0, 0)


def test_divide_zero_by_nonzero():
    assert divide(0, 5) == 0

# Edge cases with large numbers

def test_large_numbers_add():
    assert add(10**18, 10**18) == 2 * 10**18


def test_large_numbers_multiply():
    assert multiply(10**9, 10**9) == 10**18


def test_very_small_floats():
    assert add(1e-10, 2e-10) == pytest.approx(3e-10)
    assert multiply(1e-5, 1e-5) == pytest.approx(1e-10)

# Test that operations work with int and float mixtures

def test_mixed_int_float():
    assert add(2, 3.5) == pytest.approx(5.5)
    assert subtract(5, 2.5) == pytest.approx(2.5)
    assert multiply(3, 2.5) == pytest.approx(7.5)
    assert divide(7, 2.0) == pytest.approx(3.5)
