import pytest

from lib.utils.schemas.game import ResourceType
from services.api.app.apps.inventory import logic


class TestGetUserInventory:
    @pytest.mark.asyncio
    async def test_get_non_existing_inventory(
        self,
        # service fixtures
        db_connection,
        user_factory,
    ):
        """
        Тут у юзера еще нет сохраненного инвентаря, и мы заинзертим ему новый (дефолтный пустой список)
        """
        user = await user_factory()
        user_id = user.id

        result = await logic.get_user_inventory(db_connection, user_id)
        response_json = result
        assert response_json == {"slots": []}

        stored = await db_connection.fetchval(
            "SELECT data::jsonb FROM user_inventory WHERE id = $1",
            user_id,
        )
        assert stored == response_json
        assert await logic.get_user_inventory(db_connection, user_id) == result

    @pytest.mark.asyncio
    async def test_get_existing_inventory(
        self,
        # service fixtures
        db_connection,
        user_factory,
        # fixtures for test
        user_inventory_factory,
    ):
        user = await user_factory()
        user_id = user.id

        await user_inventory_factory(
            id=user_id,
            data={"slots": [ResourceType.FIRST_AID_KITS, ResourceType.MEGA_BOMBS]},
        )

        result = await logic.get_user_inventory(db_connection, user_id)
        response_json = result
        assert response_json == {"slots": [ResourceType.FIRST_AID_KITS, ResourceType.MEGA_BOMBS]}

        stored = await db_connection.fetchval(
            "SELECT data::jsonb FROM user_inventory WHERE id = $1",
            user_id,
        )
        assert stored == response_json
        assert await logic.get_user_inventory(db_connection, user_id) == result
