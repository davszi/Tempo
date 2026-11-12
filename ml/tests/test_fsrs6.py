"""Check tempo_sim.fsrs6 against the reference py-fsrs implementation.

Run:  python -m pytest tests/   (needs `pip install fsrs`)
"""
import random

import numpy as np
import pytest

fsrs = pytest.importorskip("fsrs")

from tempo_sim.fsrs6 import DEFAULT_W, FSRS6, LOWER_W, UPPER_W


def _random_weights(rng):
    w = DEFAULT_W * np.exp(rng.normal(0, 0.2, 21))
    return np.clip(w, LOWER_W, UPPER_W)


def test_defaults_match_reference():
    assert np.allclose(DEFAULT_W, fsrs.scheduler.DEFAULT_PARAMETERS)
    assert np.allclose(LOWER_W, fsrs.scheduler.LOWER_BOUNDS_PARAMETERS)
    assert np.allclose(UPPER_W, fsrs.scheduler.UPPER_BOUNDS_PARAMETERS)


@pytest.mark.parametrize("seed", range(20))
def test_transitions_match_reference(seed):
    rng = np.random.default_rng(seed)
    w = _random_weights(rng)
    ours = FSRS6(w)
    ref = fsrs.Scheduler(parameters=tuple(w))
    R = fsrs.Rating
    for _ in range(50):
        g = int(rng.integers(1, 5))
        s = float(rng.uniform(0.1, 200))
        d = float(rng.uniform(1, 10))
        t = float(rng.uniform(1, 300))
        r = ours.retrievability(t, s)
        assert r == pytest.approx(
            (1 + ref._FACTOR * t / s) ** ref._DECAY, rel=1e-9)
        assert ours.next_stability(d, s, r, g) == pytest.approx(
            ref._next_stability(difficulty=d, stability=s, retrievability=r,
                                rating=R(g)), rel=1e-9)
        assert ours.next_difficulty(d, g) == pytest.approx(
            ref._next_difficulty(difficulty=d, rating=R(g)), rel=1e-9)
        assert ours.short_term_stability(s, g) == pytest.approx(
            ref._short_term_stability(stability=s, rating=R(g)), rel=1e-9)
        st = ours.init_state(g)
        assert st.stability == pytest.approx(ref._initial_stability(rating=R(g)))
        assert st.difficulty == pytest.approx(
            ref._initial_difficulty(rating=R(g), clamp=True))
