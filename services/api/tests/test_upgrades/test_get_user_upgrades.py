import copy

import pytest

from lib.utils.schemas.game import DEFAULT_USER_UPGRADES, UpgradeSubtype, UpgradeType
from services.api.app.apps.upgrades import logic


class TestGetUserUpgrades:
    @pytest.mark.asyncio
    async def test_get_non_existing_upgrades(
        self,
        # service fixtures
        db_connection,
        # fixtures for test
        user_factory,
    ):
        """
        Тут у юзера еще нет сохраненных прокачек, и мы заинзертим ему новых (дефолтных)
        """
        user = await user_factory()
        user_id = user.id

        result = await logic.get_user_upgrades(db_connection, user_id)
        response_json = result
        assert response_json == DEFAULT_USER_UPGRADES

        stored = await db_connection.fetchval(
            "SELECT data::jsonb FROM user_upgrades WHERE id = $1",
            user_id,
        )
        assert stored == response_json
        assert await logic.get_user_upgrades(db_connection, user_id) == result

    @pytest.mark.asyncio
    async def test_get_already_existing_upgrades(
        self,
        # service fixtures
        db_connection,
        # fixtures for test
        user_factory,
        user_upgrades_factory,
    ):
        """
        А тут у юзера уже есть какие-то прокачки, соответственно вернутся они
        """
        user = await user_factory()
        user_id = user.id

        upgrades = copy.deepcopy(DEFAULT_USER_UPGRADES)
        upgrades[UpgradeType.RESOURCES][UpgradeSubtype.MAX_CARDS_IN_DECK] = 1

        await user_upgrades_factory(
            id=user_id,
            data=upgrades,
        )

        result = await logic.get_user_upgrades(db_connection, user_id)
        response_json = result
        assert response_json == upgrades

        stored = await db_connection.fetchval(
            "SELECT data::jsonb FROM user_upgrades WHERE id = $1",
            user_id,
        )
        assert stored == response_json
        assert await logic.get_user_upgrades(db_connection, user_id) == result
