from typing import Annotated

from pydantic import BaseModel, ConfigDict, FiniteFloat, StringConstraints

class OpenLightTable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reel: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    eligible: bool
