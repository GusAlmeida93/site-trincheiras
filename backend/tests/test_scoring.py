import pytest

from app.services.scoring import ScoringRules


def test_defaults_match_the_seeded_rules():
    assert ScoringRules.from_config({}) == ScoringRules(10, -5, 2)
    assert ScoringRules.from_config(None) == ScoringRules(10, -5, 2)


def test_reads_the_activity_config():
    rules = ScoringRules.from_config(
        {"points_correct": 20, "points_wrong": -7, "max_penalized_errors": 1}
    )
    assert rules == ScoringRules(20, -7, 1)


@pytest.mark.parametrize("bad", ["10", None, True, 2.5, [1], {"n": 1}])
def test_malformed_values_fall_back_to_defaults(bad):
    rules = ScoringRules.from_config(
        {"points_correct": bad, "points_wrong": bad, "max_penalized_errors": bad}
    )
    assert rules == ScoringRules()


def test_integral_floats_are_accepted():
    # JSON has one number type; 10.0 is a legitimate way to write ten.
    assert ScoringRules.from_config({"points_correct": 10.0}).points_correct == 10


def test_correct_answer_scores_regardless_of_earlier_errors():
    rules = ScoringRules()
    assert rules.score_delta(True, 0) == 10
    assert rules.score_delta(True, 7) == 10


def test_wrong_answers_stop_costing_points_at_the_cap():
    rules = ScoringRules()
    assert [rules.score_delta(False, n) for n in range(4)] == [-5, -5, 0, 0]


def test_cap_of_zero_never_penalizes():
    rules = ScoringRules(max_penalized_errors=0)
    assert rules.score_delta(False, 0) == 0
