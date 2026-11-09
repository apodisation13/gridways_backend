import pytest

from httpx import AsyncClient
from lib.utils.schemas.game import DEFAULT_USER_UPGRADES
from services.api.app.apps.preferences.schemas import DEFAULT_PREFERENCES


class TestGetUserProgressAPI:
    endpoint = "user-progress/{user_id}"

    @pytest.mark.usefixtures("init_db_cards")
    @pytest.mark.asyncio
    async def test_get_user_progress(
        self,
        # service fixtures
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        user_resource_factory,
        user_level_factory,
        user_season_factory,
        user_deck_factory,
        user_card_factory,
        user_leader_factory,
    ):
        """Прогресс включает инвентарь, настройки и прокачки пользователя."""
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        await user_resource_factory(id=user_id)

        await user_level_factory(user_id=user_id, level_id=1)
        await user_season_factory(user_id=user_id, season_id=1)

        await user_card_factory(
            user_id=user_id,
            card_id=1,
        )
        await user_leader_factory(
            leader_id=1,
            user_id=user_id,
        )

        await user_deck_factory(
            user_id=user_id,
            deck_id=1,
        )

        response = await client.get(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        response_json = response.json()
        assert set(response_json) == {
            "user_resources",
            "user_cards",
            "user_leaders",
            "user_decks",
            "user_seasons",
            "user_inventory",
            "user_preferences",
            "user_upgrades",
        }
        assert response_json["user_inventory"] == {"slots": []}
        assert response_json["user_preferences"] == {"data": DEFAULT_PREFERENCES}
        assert response_json["user_upgrades"] == DEFAULT_USER_UPGRADES
