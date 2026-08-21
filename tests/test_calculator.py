import pytest

from calculator import future_value, investment_summary, milestone_months, monthly_series, months_to_target


def test_zero_percent_future_value():
    assert future_value(3, 0, 240) == 720


def test_five_percent_future_value_is_about_1233_man_yen():
    assert future_value(3, 5, 240) == pytest.approx(1233.1, abs=0.2)


def test_five_percent_target_is_17_year_6_months():
    assert months_to_target(3, 5, 1000) == 210


def test_zero_percent_target_rounds_up_months():
    assert months_to_target(3, 0, 1000) == 334


def test_summary_series_and_milestones_are_consistent():
    summary = investment_summary(3, 5, 12)
    series = monthly_series(3, 5, 12)
    assert series[-1]["total"] == pytest.approx(summary["total"])
    assert summary["principal"] + summary["profit"] == pytest.approx(summary["total"])
    assert set(milestone_months(3, 5)) == {500, 1000, 2000}


@pytest.mark.parametrize("monthly", [0, -1])
def test_invalid_monthly_amount(monthly):
    with pytest.raises(ValueError):
        future_value(monthly, 5, 12)

