"""FastAPI endpoint and legacy CSV flag tests."""
import json
import pytest
from pydantic import ValidationError
from fastapi import HTTPException
from agents.api import NNTRequest, api_nnt
from cli import _csv_boolean


def test_api_nnt_independent_counts():
    request = NNTRequest(control_events=120,control_total=1000,
                         treatment_events=80,treatment_total=1000)
    result = api_nnt(request)
    assert result["measure"] == "NNT"
    assert result["number_needed_rounded_up"] == 25


def test_api_bad_counts_return_422():
    with pytest.raises(HTTPException) as err:
        api_nnt(NNTRequest(control_events=11,control_total=10,
                           treatment_events=0,treatment_total=10))
    assert err.value.status_code == 422


def test_api_counts_are_strict_integers():
    with pytest.raises(ValidationError):
        NNTRequest(control_events="12",control_total=100,
                   treatment_events=8,treatment_total=100)


@pytest.mark.parametrize("value, expected", [
    ("false",False),("0",False),("TRUE",True),("yes",True),("",False),(None,False)
])
def test_csv_boolean(value,expected):
    assert _csv_boolean(value) is expected


def test_csv_boolean_rejects_ambiguous_values():
    with pytest.raises(ValueError):
        _csv_boolean("sometimes")
