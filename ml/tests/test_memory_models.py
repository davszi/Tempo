"""Hidden memory models of the synthetic clients (in memory, no dataset)."""

import pytest

from tempo_ml.simulator import ARCHETYPES, MultiplicativeStability, next_reps, retrievability


@pytest.mark.parametrize("arch", list(ARCHETYPES))
def test_retrievability_is_0_9_at_t_equals_S(arch):
    C = ARCHETYPES[arch].C
    assert retrievability(3.0, 3.0, C) == pytest.approx(0.9)


def test_retrievability_boundaries():
    assert retrievability(0.0, 2.0, 0.5) == 1.0
    assert retrievability(1000.0, 1.0, 0.5) < 0.2
    assert retrievability(1.0, 2.0, 0.5) > retrievability(5.0, 2.0, 0.5)


def test_reps_soft_penalty():
    assert next_reps(5, blundered=False) == 6
    assert next_reps(5, blundered=True) == 3
    assert next_reps(1, blundered=True) == 0


def test_lapse_never_increases_stability():
    m = MultiplicativeStability()
    assert m.after_lapse(10.0, 0.3) == pytest.approx(3.0)
    assert m.after_lapse(2.0, 0.3) == pytest.approx(1.0)
    assert m.after_lapse(0.5, 0.3) == 0.5
