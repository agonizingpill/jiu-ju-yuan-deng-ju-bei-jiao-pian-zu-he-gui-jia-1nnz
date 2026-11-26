from typing import Annotated

from pydantic import BaseModel, ConfigDict, FiniteFloat, StringConstraints

class StoreProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    box: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    profile: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class PullProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    box: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    profile: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
