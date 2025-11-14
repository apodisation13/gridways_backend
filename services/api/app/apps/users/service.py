from lib.utils.db.pool import db
from services.api.app.apps.users.schemas import UsersList


class UserService:
    def __init__(self):
        self.db_pool = db

    async def get_users(self) -> list[UsersList]:
        async with self.db_pool.connection() as conn:
            result = await conn.fetch("""select id, username, email from users""")

            print(result)

        # users = [
        #     UsersList(id=row['id'], username=row['username'], email="s")
        #     for row in result
        # ]

        # return [UsersList(**dict(row)) for row in result]
        return [UsersList.model_validate(dict(row)) for row in result]
