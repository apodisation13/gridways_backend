from fastapi import APIRouter, Depends, Path
from services.api.app.apps.auth import dependencies as auth_dependencies
from services.api.app.apps.inventory.schemas import PatchInventoryRequest
from services.api.app.apps.inventory.service import InventoryService
from services.api.app.dependencies import get_inventory_service


router = APIRouter()


@router.get("/user-inventory/{user_id}")
async def get_user_inventory(
    _=Depends(auth_dependencies.validate_user),
    service: InventoryService = Depends(get_inventory_service),
    user_id: int = Path(..., gt=0),
) -> dict:
    return await service.get_inventory(user_id=user_id)


@router.patch("/user-inventory/{user_id}")
async def change_user_upgrades(
    patch_inventory_request: PatchInventoryRequest,
    _=Depends(auth_dependencies.validate_user),
    service: InventoryService = Depends(get_inventory_service),
    user_id: int = Path(..., gt=0),
) -> dict:
    return await service.change_inventory(
        user_id=user_id,
        slots=patch_inventory_request.slots,
    )
