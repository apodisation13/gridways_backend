from fastapi import APIRouter, Depends
from services.api.app.apps.achievements.service import AchievementsService
from services.api.app.apps.auth import dependencies as auth_dependencies
from services.api.app.dependencies import get_achievements_service


router = APIRouter()


@router.get("")
async def get_achievements(
    _=Depends(auth_dependencies.is_user_authorized),
    service: AchievementsService = Depends(get_achievements_service),
) -> dict:
    return await service.get_achievements()
