"""Schema tests: condition parsing and rejection, meta defaults and IDs, room rules."""

import pytest
import yaml
from pydantic import TypeAdapter, ValidationError

from casebook.case.conditions import AllOf, ClueFound, Condition, Not, StressAtLeast
from casebook.case.models import Meta, MysteryType, Room

conditions: TypeAdapter[Condition] = TypeAdapter(Condition)


def parse_condition(text: str) -> Condition:
    return conditions.validate_python(yaml.safe_load(text))


def test_single_key_picks_the_condition_type() -> None:
    assert parse_condition("{ clue_found: cellar_key }") == ClueFound(clue_found="cellar_key")


def test_nested_combinators() -> None:
    cond = parse_condition("""
        all:
          - { act_at_least: 2 }
          - not: { stress_at_least: 70 }
    """)
    assert isinstance(cond, AllOf)
    inner = cond.all[1]
    assert isinstance(inner, Not)
    assert inner.not_ == StressAtLeast(stress_at_least=70)


def test_unknown_condition_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_condition("{ clue_seen: cellar_key }")


def test_two_keys_in_one_condition_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_condition("{ clue_found: cellar_key, act_at_least: 2 }")


def test_empty_all_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_condition("{ all: [] }")


def test_stress_is_capped_at_100() -> None:
    with pytest.raises(ValidationError):
        parse_condition("{ stress_at_least: 150 }")


def test_meta_defaults() -> None:
    meta = Meta.model_validate(
        {
            "id": "vanishing-sapphire",
            "title": "The Vanishing Sapphire",
            "mystery_type": "theft",
            "theme": "country_manor",
            "difficulty": 1,
        }
    )
    assert meta.schema_version == 1
    assert meta.mystery_type is MysteryType.THEFT
    assert meta.vocabulary.culprit == "culprit"


@pytest.mark.parametrize("bad_id", ["Vanishing-Sapphire", "vanishing_sapphire", "-sapphire"])
def test_case_id_must_be_kebab_case(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        Meta.model_validate(
            {"id": bad_id, "title": "t", "mystery_type": "theft", "theme": "x", "difficulty": 1}
        )


def test_locked_room_with_unlock_condition() -> None:
    room = Room.model_validate(
        yaml.safe_load("""
            id: cellar
            name: Wine Cellar
            description: Cold and damp.
            locked: true
            unlock: { clue_found: cellar_key }
        """)
    )
    assert room.unlock == ClueFound(clue_found="cellar_key")


def test_unlock_condition_on_open_room_is_rejected() -> None:
    with pytest.raises(ValidationError, match="not locked"):
        Room.model_validate(
            {
                "id": "study",
                "name": "Study",
                "description": "Oak panels.",
                "unlock": {"clue_found": "cellar_key"},
            }
        )


def test_typo_in_field_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Room.model_validate({"id": "study", "name": "Study", "description": "x", "lockd": True})


def test_case_models_are_frozen() -> None:
    room = Room(id="study", name="Study", description="x")
    with pytest.raises(ValidationError):
        room.name = "Library"  # type: ignore[misc]
