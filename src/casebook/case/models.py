"""Pydantic schema for the case file.

Built up section by section. So far: meta, public, rooms, facts, suspects.

Meta:
- schema_version is fixed to 1 and bumped when the schema changes in a way old case files
  can't load, so a file written for another schema fails loudly instead of half-loading.
- mystery_type is a closed list; theme is open-ended on purpose ("country_manor",
  "film_set", ...).
- vocabulary holds the words player-facing text uses, so a theft says "thief" rather
  than "killer".

Public is what the player sees when the game starts: brief, setting, start room.

Room: a locked room may have an unlock condition that opens it by itself. A locked room
without one is allowed, because an event effect can open it. An unlock condition on a room
that isn't locked is rejected.

Fact (server only): one atomic piece of the hidden truth, e.g. "Voss swaps the sapphire for
a paste copy in the study". Lies, secrets, cracks, clues and the solution all point at fact
ids, which is what lets code check fairness and leaks without an LLM. ``time`` is "HH:MM"
and must be quoted in YAML: PyYAML reads an unquoted 21:40 as the integer 1300, which is
rejected here rather than silently turned into a wrong time.

Suspect has two blocks:
- public: name, role, description. Safe to show the player.
- private: only ever sent to that suspect's own agent and to the continuity checker.
  - personality, voice: how the agent speaks.
  - did, saw, knows: fact ids for what the suspect did, witnessed, and heard second hand.
    The agent is told the text of these facts and nothing else of the truth.
  - alibi: what the suspect claims when asked where they were. If it's false, a lie
    covers the fact it hides.
  - secret: a fact id the suspect protects and only admits when cracked.
  - lies: sanctioned lies. ``claim`` is what they say, ``covers`` the fact id it hides.
    The continuity checker treats these as allowed; any other untruth is a violation.
  - cracks: when ``when`` holds, the suspect admits the ``reveals`` facts. A crack may only
    reveal the suspect's own secret or a fact one of their lies covers. ``when`` may use
    the suspect-scoped conditions (confronted_with, stress_at_least).
  - relationships: other suspect id -> how this suspect feels about them.
- starts_in: room id where the suspect is at the start.

Checks that need the whole case (fact ids exist, rooms exist, relationship targets are
real suspects) belong to the case validator, not to these models.
"""

from enum import StrEnum
from typing import Annotated, Final, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from casebook.case.base import CaseModel, Id, Slug
from casebook.case.conditions import Condition

SCHEMA_VERSION: Final = 1


class MysteryType(StrEnum):
    THEFT = "theft"
    DISAPPEARANCE = "disappearance"
    FRAUD = "fraud"
    SABOTAGE = "sabotage"
    BLACKMAIL = "blackmail"
    FORGERY = "forgery"
    MURDER = "murder"


class Vocabulary(CaseModel):
    culprit: str = "culprit"
    method: str = "method"


class Meta(CaseModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    id: Slug
    title: str
    mystery_type: MysteryType
    theme: str
    difficulty: Annotated[int, Field(ge=1, le=5)]
    vocabulary: Vocabulary = Vocabulary()


class Public(CaseModel):
    brief: str
    setting: str
    start_room: Id


class Room(CaseModel):
    id: Id
    name: str
    description: str
    locked: bool = False
    unlock: Condition | None = None

    @model_validator(mode="after")
    def _unlock_only_if_locked(self) -> Self:
        if self.unlock is not None and not self.locked:
            raise ValueError(f"room {self.id!r} has an unlock condition but is not locked")
        return self


type ClockTime = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class Fact(CaseModel):
    id: Id
    text: str
    time: ClockTime | None = None


class SuspectPublic(CaseModel):
    name: str
    role: str
    description: str


class Lie(CaseModel):
    id: Id
    claim: str
    covers: Id


class CrackRule(CaseModel):
    when: Condition
    reveals: Annotated[list[Id], Field(min_length=1)]


class SuspectPrivate(CaseModel):
    personality: str
    voice: str
    did: list[Id] = []
    saw: list[Id] = []
    knows: list[Id] = []
    alibi: str
    secret: Id | None = None
    lies: list[Lie] = []
    cracks: list[CrackRule] = []
    relationships: dict[Id, str] = {}


class Suspect(CaseModel):
    id: Id
    public: SuspectPublic
    private: SuspectPrivate
    starts_in: Id

    @model_validator(mode="after")
    def _check_own_references(self) -> Self:
        lie_ids = [lie.id for lie in self.private.lies]
        if len(lie_ids) != len(set(lie_ids)):
            raise ValueError(f"suspect {self.id!r} has duplicate lie ids")

        if self.id in self.private.relationships:
            raise ValueError(f"suspect {self.id!r} has a relationship with themself")

        revealable = {lie.covers for lie in self.private.lies}
        if self.private.secret is not None:
            revealable.add(self.private.secret)
        for crack in self.private.cracks:
            unknown = [fact for fact in crack.reveals if fact not in revealable]
            if unknown:
                raise ValueError(
                    f"suspect {self.id!r} crack reveals {unknown}, "
                    "which is neither their secret nor covered by one of their lies"
                )
        return self
