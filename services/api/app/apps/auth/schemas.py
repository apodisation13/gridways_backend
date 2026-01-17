from pydantic import Field, EmailStr

from lib.utils.schemas import Base


class UserRegisterRequest(Base):
    username: str = Field(
        ...,
        min_length=5,
        max_length=50,
    )
    email: EmailStr
    password: str = Field(
        ...,
        min_length=5,
        max_length=50,
    )


class UserRegisterResponse(Base):
    id: int
    username: str
    email: str


class UserLoginRequest(Base):
    email: EmailStr
    password: str = Field(
        ...,
        min_length=5,
        max_length=50,
    )


class Token(Base):
    access_token: str
    token_type: str


class UserLoginResponse(Base):
    id: int
    username: str
    email: str
    token: Token


class UserCheckTokenResponse(Base):
    id: int
    email: str
