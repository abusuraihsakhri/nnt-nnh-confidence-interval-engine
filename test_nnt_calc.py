"""Regression tests for independent-group NNT/NNH and CSV export."""
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest
from nnt_calc import calculate_metrics, process_batch, main


def test_benefit_known_example():
    r = calculate_metrics(120, 1000, 80, 1000)
    assert r["measure"] == "NNT"
    assert r["absolute_risk_reduction"] == pytest.approx(0.04)
    assert r["relative_risk"] == pytest.approx(2 / 3)
    assert r["relative_risk_reduction"] == pytest.approx(1 / 3)
    assert r["number_needed"] == pytest.approx(25)
    assert r["number_needed_rounded_up"] == 25
    assert r["risk_difference_ci"] == pytest.approx([0.013718313895640582, 0.06644947071003807])
    assert r["number_needed_ci"] == pytest.approx([1 / 0.06644947071003807, 1 / 0.013718313895640582])
    assert not r["ci_crosses_zero"]


def test_harm_reverses_contrast():
    r = calculate_metrics(80, 1000, 120, 1000)
    assert r["measure"] == "NNH"
    assert r["number_needed"] == pytest.approx(25)
    assert r["risk_difference_ci"] == pytest.approx([-0.06644947071003807, -0.013718313895640582])
    assert r["number_needed_ci"][0] > 0


@pytest.mark.parametrize("c,n,t,m", [
    (0, 100, 0, 100),
    (50, 100, 50, 100),
    (100, 100, 100, 100),
])
def test_equal_risks_no_finite_nnt(c,n,t,m):
    r = calculate_metrics(c,n,t,m)
    assert r["number_needed"] is None
    assert r["number_needed_ci"] is None
    assert r["ci_crosses_zero"]
    assert r["measure"] == "no_difference"


def test_ci_crossing_null_not_inverted_to_finite():
    r = calculate_metrics(11,100,10,100)
    assert r["measure"] == "NNT"
    assert r["number_needed"] == pytest.approx(100)
    assert r["number_needed_ci"] is None
    assert r["ci_crosses_zero"]
    assert r["risk_difference_ci"][0] < 0 < r["risk_difference_ci"][1]


def test_zero_event_group_and_complete_events():
    r = calculate_metrics(2,100,0,100)
    assert r["number_needed"] == pytest.approx(50)
    assert all(-1 <= x <= 1 for x in r["risk_difference_ci"])
    r = calculate_metrics(100,100,0,100)
    assert r["number_needed"] == pytest.approx(1)
    assert r["number_needed_ci"] is not None


@pytest.mark.parametrize("input_args", [
    (-1,100,0,100), (101,100,0,100), (0,0,0,100),
    (0,100,1,0), (0,100,-1,100), (0,100,101,100),
    (True,100,1,100), (0,100.5,1,100), (0,100,1,"100"),
])
def test_invalid_event_counts(input_args):
    with pytest.raises(ValueError):
        calculate_metrics(*input_args)


@pytest.mark.parametrize("level", [float("nan"),float("inf"),0.0,1.0,-0.2,True,"0.95"])
def test_invalid_confidence(level):
    with pytest.raises(ValueError):
        calculate_metrics(1,10,0,10,level)


@pytest.mark.parametrize("level", [.9,.95,.99])
def test_confidence_width_monotonic_and_contains_estimate(level):
    r = calculate_metrics(80,500,50,500,level)
    lo, hi = r["risk_difference_ci"]
    assert lo <= r["absolute_risk_reduction"] <= hi
    assert -1 <= lo < hi <= 1


def test_larger_confidence_wider_interval():
    small = calculate_metrics(80,500,50,500,.9)["risk_difference_ci"]
    large = calculate_metrics(80,500,50,500,.99)["risk_difference_ci"]
    assert large[0] < small[0] and large[1] > small[1]


def test_relative_risk_undefined_with_zero_control_events():
    r = calculate_metrics(0, 100, 1, 100)
    assert r["relative_risk"] is None
    assert r["relative_risk_reduction"] is None


def test_batch_atomic_and_preserves_identifier(tmp_path):
    src, dst = tmp_path/"src.csv", tmp_path/"dst.csv"
    src.write_text("study_id,control_events,control_total,treatment_events,treatment_total\n"
                   "Trial A,120,1000,80,1000\nTrial B,5,100,10,100\n", encoding="utf-8")
    assert process_batch(str(src),str(dst)) == 2
    with dst.open(encoding="utf-8",newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["study_id"] == "Trial A"
    assert rows[0]["number_needed_rounded_up"] == "25"
    assert rows[1]["measure"] == "NNH"


def test_batch_rejects_bad_header(tmp_path):
    src, dst = tmp_path/"in.csv", tmp_path/"out.csv"
    src.write_text("v1,v2\n2,3\n")
    with pytest.raises(ValueError,match="required"):
        process_batch(str(src),str(dst))
    assert not dst.exists()


def test_batch_invalid_row_leaves_existing_output_intact(tmp_path):
    src, dst = tmp_path/"in.csv", tmp_path/"out.csv"
    src.write_text("control_events,control_total,treatment_events,treatment_total\n"
                   "3,10,1,10\ninvalid,10,1,10\n")
    dst.write_text("untouched")
    with pytest.raises(ValueError,match="row 3"):
        process_batch(str(src),str(dst))
    assert dst.read_text() == "untouched"
    assert not list(tmp_path.glob(".nnt-*.csv"))


def test_batch_never_overwrites_input(tmp_path):
    src = tmp_path/"in.csv"
    src.write_text("keep")
    with pytest.raises(ValueError,match="differ"):
        process_batch(str(src),str(src))
    assert src.read_text() == "keep"


def test_cli_single(capsys):
    assert main(["single","--control-events","120","--control-total","1000",
                 "--treatment-events","80","--treatment-total","1000"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["measure"] == "NNT"
    assert result["number_needed_rounded_up"] == 25
