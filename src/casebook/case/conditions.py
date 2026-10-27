"""The condition format used by rooms, acts, events and suspect cracks.

In the case file a condition is a mapping with exactly one key, and the key picks the type:

    { clue_found: cellar_key }
    { all: [ { act_at_least: 2 }, { actions_taken_at_least: 8 } ] }
    { not: { event_fired: e_blackout } }

This module only defines the shape. The engine evaluates conditions in plain Python;
an LLM never decides whether one holds.

Condition types:
- clue_found, clues_found_at_least, room_searched, event_fired, act_at_least: progress.
- statement_heard: the player has heard a suspect make this claim (a lie id or fact id).
- actions_taken_at_least: pacing, counted over all player actions (questions, searches,
  confrontations).
- points_below: pacing, the player's insight points balance is below the value.
- confronted_with, stress_at_least: suspect-scoped. They refer to "the suspect being
  evaluated", so they only make sense inside a suspect's crack rules; the case validator
  rejects them anywhere else. Stress runs 0-100.
- all, any, not: combinators, nestable. "not" is a Python keyword, so the attribute is
  ``not_`` and the YAML key stays "not".

Condition is a discriminated union: _condition_tag reads the single key of a raw mapping
(or the field's YAML key on an already-built model) and pydantic builds only that model.
An unknown key or a mapping with two keys returns no tag, which gives one clear error
instead of a failed attempt per condition type.
"""

from typing import Annotated, Any

from pydantic import Discriminator, Field, Tag

from casebook.case.base import CaseModel, Id

type Count = Annotated[int, Field(ge=1)]


class ClueFound(CaseModel):
    clue_found: Id


class CluesFoundAtLeast(CaseModel):
    clues_found_at_least: Count


class StatementHeard(CaseModel):
    statement_heard: Id


class RoomSearched(CaseModel):
    room_searched: Id


class ActAtLeast(CaseModel):
    act_at_least: Count


class EventFired(CaseModel):
    event_fired: Id


class ActionsTakenAtLeast(CaseModel):
    actions_taken_at_least: Count


class PointsBelow(CaseModel):
    points_below: Annotated[int, Field(ge=0)]


class ConfrontedWith(CaseModel):
    confronted_with: Id


class StressAtLeast(CaseModel):
    stress_at_least: Annotated[int, Field(ge=0, le=100)]


class AllOf(CaseModel):
    all: Annotated[list[Condition], Field(min_length=1)]


class AnyOf(CaseModel):
    any: Annotated[list[Condition], Field(min_length=1)]


class Not(CaseModel):
    not_: Condition = Field(alias="not")


def _condition_tag(value: Any) -> str | None:
    if isinstance(value, dict):
        return next(iter(value)) if len(value) == 1 else None
    if isinstance(value, CaseModel):
        name, info = next(iter(type(value).model_fields.items()))
        return info.alias or name
    return None


type Condition = Annotated[
    Annotated[ClueFound, Tag("clue_found")]
    | Annotated[CluesFoundAtLeast, Tag("clues_found_at_least")]
    | Annotated[StatementHeard, Tag("statement_heard")]
    | Annotated[RoomSearched, Tag("room_searched")]
    | Annotated[ActAtLeast, Tag("act_at_least")]
    | Annotated[EventFired, Tag("event_fired")]
    | Annotated[ActionsTakenAtLeast, Tag("actions_taken_at_least")]
    | Annotated[PointsBelow, Tag("points_below")]
    | Annotated[ConfrontedWith, Tag("confronted_with")]
    | Annotated[StressAtLeast, Tag("stress_at_least")]
    | Annotated[AllOf, Tag("all")]
    | Annotated[AnyOf, Tag("any")]
    | Annotated[Not, Tag("not")],
    Discriminator(_condition_tag),
]
