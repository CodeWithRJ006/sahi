"""Deterministic safety rules for SahiGuard."""

import math
from typing import Tuple, List, Optional

# Pairs of numbers easily confused across Indic/English phonetics
# e.g., 15 vs 50 (pandrah vs pachas, fifteen vs fifty, padihenu vs yabhai)
# 17 vs 70 (satrah vs sattar, seventeen vs seventy, padihedu vs debbai)
PHONETIC_CONFUSABLE_BASES = {
    (15, 50), (50, 15),
    (17, 70), (70, 17),
    (19, 90), (90, 19),
    (13, 30), (30, 13),
    (14, 40), (40, 14),
    (16, 60), (60, 16),
    (18, 80), (80, 18),
}

def is_power_of_ten_discrepancy(amt1: int, amt2: int) -> Tuple[bool, float]:
    """
    Checks if two amounts differ by a factor of 10, 100, 1000, etc.
    Returns (is_power_of_ten, ratio).
    """
    if amt1 <= 0 or amt2 <= 0:
        return False, 0.0
    if amt1 == amt2:
        return False, 1.0

    ratio = max(amt1, amt2) / min(amt1, amt2)
    # Check if ratio is very close to 10^k
    log10_val = math.log10(ratio)
    if abs(log10_val - round(log10_val)) < 1e-4:
        return True, round(ratio, 2)
    return False, round(ratio, 2)

def is_phonetic_confusable(amt1: int, amt2: int) -> bool:
    """
    Checks if two amounts share a base that matches a known phonetic confusion
    scaled by powers of 10 (e.g. 15,000 vs 50,000, or 1,700 vs 7,000, or 17 vs 70).
    """
    if amt1 <= 0 or amt2 <= 0 or amt1 == amt2:
        return False

    # Normalize by trailing zeroes
    for base1, base2 in PHONETIC_CONFUSABLE_BASES:
        for scale in [1, 10, 100, 1_000, 10_000, 100_000]:
            if (amt1 == base1 * scale and amt2 == base2 * scale) or \
               (amt1 == base2 * scale and amt2 == base1 * scale):
                return True
    return False

def check_high_value_limit(amount: int, threshold: int = 50_000) -> bool:
    """Returns True if amount exceeds the automated straight-through execution limit."""
    return amount > threshold
