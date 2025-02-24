from enum import Enum

from pydantic import BaseModel, Field


class AuthEnum(str, Enum):
    userpass = 'userpass'
    token = 'token'
    approle = 'approle'

class ConfigParams(BaseModel):
    server: str
    path: str
    key: str
    auth_method: AuthEnum = Field(default=AuthEnum.userpass)
    kv_version: int = Field(default=2)
    mount_point: str = Field(default='kv')

