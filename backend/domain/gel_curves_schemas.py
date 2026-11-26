from typing import Annotated

from pydantic import BaseModel, ConfigDict, FiniteFloat, StringConstraints

class ScanGel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    reel: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    bands: list | dict


class RecheckCurve(BaseModel):
    model_config = ConfigDict(extra="forbid")
    curve: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
