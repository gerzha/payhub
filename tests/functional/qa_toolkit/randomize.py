from random import randint


def generate_random_int_unique(base: int = 1_000_000) -> int:
    return randint(base, base * 10)
