"""Human-readable order numbers: SR + year + padded id."""
from datetime import datetime


def format_order_number(pk: int) -> str:
    year = datetime.now().year % 100
    return f'SR{year}{pk:05d}'
