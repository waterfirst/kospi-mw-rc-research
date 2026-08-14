import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from final_open_research import (
    extreme_ewy_gapup_underreaction_watch,
    post_rally_risk_on_open_underreaction_watch,
)
from kospi_1230_final_model_run import detect_concentrated_rally_late_fade_risk


def test_concentrated_rally_late_fade_guard_matches_two_scored_cases():
    program = {"program": {"total": 3062.0}}
    assert detect_concentrated_rally_late_fade_risk(program, 0.2194, 1.196, 1.0, 33.23, 28.66)
    program["program"]["total"] = 6277.0
    assert detect_concentrated_rally_late_fade_risk(program, -0.0915, 3.292, 0.9681, 19.94, 5.17)


def test_concentrated_rally_late_fade_guard_rejects_broad_rally():
    assert not detect_concentrated_rally_late_fade_risk(
        {"program": {"total": 6277.0}}, 0.40, 3.292, 0.98, 20.0, 6.0
    )


def test_extreme_ewy_gapup_watch_matches_two_scored_underreactions():
    def us(ewy, sox, nasdaq, sp500):
        return {"ewy": {"change_pct": ewy}, "sox": {"change_pct": sox},
                "nasdaq": {"change_pct": nasdaq}, "sp500": {"change_pct": sp500}}

    assert extreme_ewy_gapup_underreaction_watch(us(6.80, 6.55, 2.59, 1.79), {"change_pct": 0.067})
    assert extreme_ewy_gapup_underreaction_watch(us(5.16, 2.49, 0.54, 0.26), {"change_pct": 0.333})


def test_extreme_ewy_gapup_watch_rejects_non_extreme_control():
    us = {"ewy": {"change_pct": 4.99}, "sox": {"change_pct": 2.49},
          "nasdaq": {"change_pct": 0.54}, "sp500": {"change_pct": 0.26}}
    assert not extreme_ewy_gapup_underreaction_watch(us, {"change_pct": 0.10})


def test_post_rally_risk_on_watch_matches_aug_13_and_14_misses():
    us = {"ewy": {"change_pct": 1.56}, "nasdaq": {"change_pct": 0.81}, "sp500": {"change_pct": 0.65}}
    domestic = {"foreign": 21100, "institution": 6830, "samsung_pct": 4.89, "skhynix_pct": 5.92}
    assert post_rally_risk_on_open_underreaction_watch(us, {"change_pct": 0.117}, domestic, 0.0356)
    us["ewy"]["change_pct"] = 5.16
    domestic.update({"foreign": 28350, "institution": 5280, "samsung_pct": 6.68, "skhynix_pct": 5.54})
    assert post_rally_risk_on_open_underreaction_watch(us, {"change_pct": 0.333}, domestic, 0.0368)


def test_post_rally_risk_on_watch_rejects_low_ewy_control():
    us = {"ewy": {"change_pct": 1.49}, "nasdaq": {"change_pct": 0.81}, "sp500": {"change_pct": 0.65}}
    domestic = {"foreign": 21100, "institution": 6830, "samsung_pct": 4.89, "skhynix_pct": 5.92}
    assert not post_rally_risk_on_open_underreaction_watch(us, {"change_pct": 0.117}, domestic, 0.0356)
