from fastapi import APIRouter, Depends, Request
from services.api.app.apps.auth import dependencies as auth_dependencies
from services.api.app.apps.game_data.schemas import GameDataResponse
from services.api.app.apps.game_data.service import GameDataService
from services.api.app.dependencies import get_game_data_service


router = APIRouter()


@router.get("")
async def get_game_data(
    request: Request,
    _=Depends(auth_dependencies.is_user_authorized),
    service: GameDataService = Depends(get_game_data_service),
) -> GameDataResponse:
    return await service.get_game_data(
        base_url=str(request.base_url),
    )
