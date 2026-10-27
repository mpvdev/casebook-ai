"""Schema tests for facts and suspects: parsing, quoted times, and a suspect's own references."""

from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from casebook.case.conditions import AnyOf
from casebook.case.models import Fact, Suspect

GRAVES = """
id: graves
public:
  name: Mr Graves
  role: Butler, 30 years' service
  description: Immaculate, unreadable.
private:
  personality: formal, protective of the family, dry humour
  voice: clipped, never uses first names
  did: [f_graves_out]
  saw: [f_voss_corridor]
  knows: [f_clara_elope]
  alibi: Serving in the dining room from nine until half past ten.
  secret: f_graves_debt
  lies:
    - id: l_graves_dining
      claim: I never left the dining room all evening.
      covers: f_graves_out
  cracks:
    - when: { any: [ { confronted_with: cellar_receipt }, { stress_at_least: 70 } ] }
      reveals: [f_graves_debt, f_graves_out]
  relationships:
    clara: Watched her grow up; will cover for her.
starts_in: dining_room
"""


def graves(**private_overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(GRAVES)
    data["private"].update(private_overrides)
    return data


def test_full_suspect_parses() -> None:
    suspect = Suspect.model_validate(graves())
    assert suspect.public.name == "Mr Graves"
    assert suspect.private.lies[0].covers == "f_graves_out"
    assert isinstance(suspect.private.cracks[0].when, AnyOf)


def test_fact_with_quoted_time() -> None:
    fact = Fact.model_validate(yaml.safe_load('{ id: f_swap, text: Swap., time: "21:40" }'))
    assert fact.time == "21:40"


def test_unquoted_time_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Fact.model_validate(yaml.safe_load("{ id: f_swap, text: Swap., time: 21:40 }"))


def test_impossible_time_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Fact.model_validate({"id": "f_swap", "text": "Swap.", "time": "25:00"})


def test_crack_cannot_reveal_an_unrelated_fact() -> None:
    cracks = [{"when": {"stress_at_least": 50}, "reveals": ["f_swap"]}]
    with pytest.raises(ValidationError, match="neither their secret"):
        Suspect.model_validate(graves(cracks=cracks))


def test_crack_must_reveal_something() -> None:
    with pytest.raises(ValidationError):
        Suspect.model_validate(graves(cracks=[{"when": {"stress_at_least": 50}, "reveals": []}]))


def test_duplicate_lie_ids_are_rejected() -> None:
    lie = {"id": "l_graves_dining", "claim": "x", "covers": "f_graves_out"}
    with pytest.raises(ValidationError, match="duplicate lie ids"):
        Suspect.model_validate(graves(lies=[lie, lie]))


def test_relationship_with_self_is_rejected() -> None:
    with pytest.raises(ValidationError, match="themself"):
        Suspect.model_validate(graves(relationships={"graves": "x"}))


def test_alibi_is_required() -> None:
    data = graves()
    del data["private"]["alibi"]
    with pytest.raises(ValidationError):
        Suspect.model_validate(data)
