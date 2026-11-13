"""Hesitation latency engine (synthetic-clients record, section 3.4).

final_time_ms = baseline_ms + total_hesitation_ms
total_hesitation_ms = raw_hesitation_s * 1000 * exp(beta * (1 - R)) / (1 + alpha * reps)
raw_hesitation_s ~ Lognormal(mu, sigma)

Context multipliers m_depth and m_sharpness (record section 5) are deferred.
"""

from __future__ import annotations

import math

import numpy as np

from .traits import ClientTraits


def cognitive_strain(beta: float, R: float) -> float:
    """exp(beta * (1 - R)); 1.0 when R = 1."""
    return math.exp(beta * (1.0 - R))


def practice_multiplier(alpha: float, reps: int) -> float:
    """1 / (1 + alpha * reps); tends to 0 as reps grows."""
    return 1.0 / (1.0 + alpha * reps)


def sample_move_time_ms(
    traits: ClientTraits,
    R: float,
    reps: int,
    rng: np.random.Generator,
) -> float:
    """Sample one move's latency in milliseconds."""
    raw_hesitation_s = rng.lognormal(mean=traits.mu, sigma=traits.sigma)
    hesitation_ms = (
        raw_hesitation_s
        * 1000.0
        * cognitive_strain(traits.beta, R)
        * practice_multiplier(traits.alpha, reps)
    )
    return traits.baseline_ms + hesitation_ms
