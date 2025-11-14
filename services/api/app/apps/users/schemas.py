from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    id: int

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class UsersList(User):
    username: str
    email: str
