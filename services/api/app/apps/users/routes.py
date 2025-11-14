from fastapi import APIRouter, Depends

# from lib.utils.db.pool import get_db_pool

from services.api.app.apps.users import schemas
from services.api.app.apps.users.service import UserService

router = APIRouter()


@router.get("/users")
async def get_users(
    service: UserService = Depends(),
) -> list[schemas.UsersList]:
    return await service.get_users()
