"""Shared base model and ID types for the case schema.

CaseModel is the parent of every model in a case file:
- extra="forbid": a typo in the YAML (``lockd: true``) is an error, not silently ignored.
- frozen=True: a loaded case never changes at runtime; game progress lives in game state.

Id is lower snake case ("cellar_key") and names everything inside a case: rooms, clues,
facts, suspects. Slug is kebab case ("vanishing-sapphire") and names the case itself, since
case IDs also appear in file names and URLs.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class CaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


type Id = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]

type Slug = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")]
