from lib.utils.schemas import Base


class User(Base):
    id: int
    username: str
    email: str
    image: str | None


class UserRegister(Base):
    username: str
    email: str
    password: str


class UserLogin(Base):
    email: str
    password: str


class Token(Base):
    access_token: str
    token_type: str
