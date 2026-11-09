from fastapi import APIRouter, Depends, Path
from services.api.app.apps.auth import dependencies as auth_dependencies
from services.api.app.apps.upgrades.schemas import PostUpgradeRequest, PostUpgradeResponse
from services.api.app.apps.upgrades.service import UpgradesService
from services.api.app.dependencies import get_upgrades_service


router = APIRouter()


@router.post("/user-upgrades/{user_id}")
async def perform_user_upgrades(
    post_upgrade_request: PostUpgradeRequest,
    _=Depends(auth_dependencies.validate_user),
    service: UpgradesService = Depends(get_upgrades_service),
    user_id: int = Path(..., gt=0),
) -> PostUpgradeResponse:
    return await service.post_user_upgrade(
        user_id=user_id,
        upgrade_type=post_upgrade_request.upgrade_type,
        upgrade_subtype=post_upgrade_request.upgrade_subtype,
    )
