import pytest

from httpx import AsyncClient
from lib.utils.schemas.game import ResourceType


class TestUserInventoryAPI:
    endpoint = "user-inventory/{user_id}"

    @pytest.mark.asyncio
    async def test_get_non_existing_inventory(
        self,
        # service fixtures
        client: AsyncClient,
        user_login_fixture,
    ):
        """
        Тут у юзера еще нет сохраненного инвентаря, и мы заинзертим ему новый (дефолтный пустой список)
        """
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        response = await client.get(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_json = response.json()
        assert response.status_code == 200
        assert response_json == {"slots": []}

    @pytest.mark.asyncio
    async def test_get_existing_inventory(
        self,
        # service fixtures
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        user_inventory_factory,
    ):
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        await user_inventory_factory(
            id=user_id,
            data={"slots": [ResourceType.FIRST_AID_KITS, ResourceType.MEGA_BOMBS]},
        )

        response = await client.get(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_json = response.json()
        assert response.status_code == 200
        assert response_json == {"slots": [ResourceType.FIRST_AID_KITS, ResourceType.MEGA_BOMBS]}

    @pytest.mark.asyncio
    async def test_change_inventory_success(
        self,
        # service fixtures
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        user_inventory_factory,
        game_constants_factory,
    ):
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        await game_constants_factory(
            data={
                "upgrades": {
                    "inventory": {
                        "upgrades": {"inventory_slots": {"upgrades": {"0": {"value": 2}}}},
                    },
                },
            },
        )

        await user_inventory_factory(
            id=user_id,
            data={"slots": [ResourceType.FIRST_AID_KITS, ResourceType.MEGA_BOMBS]},
        )

        response = await client.patch(
            self.endpoint.format(user_id=user_id),
            json={"slots": [ResourceType.IMMUNE_MAGICS, ResourceType.DRAW_CARDS]},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_json = response.json()
        assert response.status_code == 200
        assert response_json == {"slots": [ResourceType.IMMUNE_MAGICS, ResourceType.DRAW_CARDS]}

    @pytest.mark.asyncio
    async def test_change_inventory_fails(
        self,
        # service fixtures
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        game_constants_factory,
    ):
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        # кейс 1: есть повторы
        response = await client.patch(
            self.endpoint.format(user_id=user_id),
            json={"slots": [ResourceType.IMMUNE_MAGICS, ResourceType.IMMUNE_MAGICS]},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_json = response.json()
        assert response.status_code == 400
        assert response_json["error"]["message"] == "Wrong slots ['immune_magics', 'immune_magics'] for user 1"

        # кейс 2: есть те, которых быть не должно
        response = await client.patch(
            self.endpoint.format(user_id=user_id),
            json={"slots": [ResourceType.IMMUNE_MAGICS, ResourceType.MONEY]},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_json = response.json()
        assert response.status_code == 400
        assert response_json["error"]["message"] == "Wrong slot: money, for user 1"

        # кейс 3 - вот у юзера нет прокачек (или есть и уровень 0) - и там всего 2 слота, а он пытается 3
        await game_constants_factory(
            data={
                "upgrades": {
                    "inventory": {
                        "upgrades": {"inventory_slots": {"upgrades": {"0": {"value": 2}}}},
                    },
                },
            },
        )
        response = await client.patch(
            self.endpoint.format(user_id=user_id),
            json={"slots": [ResourceType.IMMUNE_MAGICS, ResourceType.DRAW_CARDS, ResourceType.MEGA_BOMBS]},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_json = response.json()
        assert response.status_code == 400
        assert response_json["error"]["message"] == "Too many inventory slots for user 1: got 3, maximum 2"
