"""认证接口的出入参。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from schorder.schemas.common import ApiModel


class UserOut(ApiModel):
    id: str
    phone: str
    nickname: str
    role: str
    avatar_url: str | None = None


class SessionDataOut(ApiModel):
    user: UserOut
    csrf_token: str


class RegisterIn(ApiModel):
    phone: str = Field(min_length=11, max_length=11)
    password: str = Field(min_length=8, max_length=64)
    nickname: str = Field(min_length=1, max_length=30)


class LoginIn(ApiModel):
    phone: str = Field(min_length=11, max_length=11)
    password: str = Field(min_length=1, max_length=64)


class ChangePasswordIn(ApiModel):
    old_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)


class SessionEnvelope(ApiModel):
    ok: Literal[True] = True
    data: SessionDataOut


class OkData(ApiModel):
    success: bool = True


class OkEnvelope(ApiModel):
    ok: Literal[True] = True
    data: OkData
