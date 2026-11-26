from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints


class BuildBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # 复测曲线由服务端统一收集，预留说明字段，保持请求体可扩展。
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)] = ''


class SaveBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class ConvertProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    profile: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class SettleConversion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    profile: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class ActivateBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline: Optional[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]] = None
