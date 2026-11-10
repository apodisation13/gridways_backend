from fastapi import APIRouter, Depends, Path
from services.api.app.apps.user_achievements.schemas import AchievementEventsRequest, AchievementEventsResponse
from services.api.app.apps.user_achievements.service import AchievementsService
from services.api.app.apps.auth import dependencies as auth_dependencies
from services.api.app.dependencies import get_achievements_service


router = APIRouter()


@router.post("/user-achievements/{user_id}")
async def update_user_achievements(
    data: AchievementEventsRequest,
    _=Depends(auth_dependencies.validate_user),
    service: AchievementsService = Depends(get_achievements_service),
    user_id: int = Path(..., gt=0),
) -> AchievementEventsResponse:
    return await service.process_events(user_id=user_id, events=data.events)
