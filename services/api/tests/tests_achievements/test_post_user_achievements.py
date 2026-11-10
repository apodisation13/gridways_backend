import asyncio
from unittest.mock import patch

import pytest

from httpx import AsyncClient
import pytest_asyncio
from services.api.app.apps.progress.logic import change_resources
from services.api.app.apps.progress.schemas import UserResources
from services.api.app.apps.user_achievements.schemas import AchievementEventsRequest
from services.api.app.apps.user_achievements.service import AchievementsService
from services.api.app.dependencies import get_db
from services.api.tests.factories.factories import GameConstantsFactory


def task(key: str, target: int, event: str = "action.played") -> dict:
    return {
        "id": key,
        "event": event,
        "target": target,
        "counter": {"type": "sum", "field": "amount"} if event == "resource.spent" else {"type": "count"},
        "filters": {"resource": "money"} if event == "resource.spent" else {"actor.color": "Bronze"},
        "rewards": {"resources": {"money": 10}},
        "title": "Test achievement",
        "ordering": 10,
    }


CARD = {"type": "action.played", "data": {"actor": {"faction": "Neutral", "id": 123, "color": "Bronze"}}}


@pytest_asyncio.fixture
async def achievements_setup(
    # service fixtures
    user_login_fixture,
    # fixtures for test
    game_constants_factory,
    user_resource_factory,
) -> tuple[int, dict[str, str]]:
    user_id = user_login_fixture["id"]
    data = {
        **GameConstantsFactory.build().data,
        "achievements": {
            "permanent": {
                "categories": {
                    "cards": {"achievements": {"bronze_2": task("bronze_2", 2), "bronze_3": task("bronze_3", 3)}},
                    "resources": {"achievements": {"spend_100": task("spend_100", 100, "resource.spent")}},
                },
            },
        },
    }
    await game_constants_factory(data=data)
    await user_resource_factory(id=user_id, money=100)
    return user_id, {"Authorization": f"Bearer {user_login_fixture['token']['access_token']}"}


class TestPostUserAchievements:
    endpoint = "user-achievements/{user_id}"

    @pytest.mark.asyncio
    async def test_progress_and_rewards(
        self,
        # service fixtures
        client: AsyncClient,
        db_connection,
        # fixtures for test
        achievements_setup,
        user_achievements_factory,
    ):
        user_id, headers = achievements_setup

        await user_achievements_factory(id=user_id, progress={"daily": {"period": "2026-11-10", "tasks": {}}})

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers=headers,
            json={"events": [CARD]},
        )

        assert response.status_code == 200

        response_json = response.json()
        assert set(response_json) == {"user_achievements", "granted_rewards", "user_resources"}
        assert response_json["user_resources"] is None
        assert response_json["granted_rewards"] == []
        assert response_json["user_achievements"]["permanent"]["bronze_2"] == {
            "value": 1,
            "completed_at": None,
            "reward_granted_at": None,
        }

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers=headers,
            json={"events": [CARD, CARD]},
        )

        assert response.status_code == 200

        response_json = response.json()
        assert response_json["user_resources"]["money"] == 120
        assert "raw_bronze" in response_json["user_resources"]
        assert {reward["achievement_id"] for reward in response_json["granted_rewards"]} == {"bronze_2", "bronze_3"}

        for reward in response_json["granted_rewards"]:
            assert reward["period_type"] == "permanent"
            assert reward["period"] is None
            assert reward["rewards"] == {"resources": {"money": 10}}

        state = response_json["user_achievements"]["permanent"]["bronze_2"]
        assert state["value"] == 2
        assert state["completed_at"] == state["reward_granted_at"]
        assert state["reward_granted_at"].endswith("Z")
        assert response_json["user_achievements"]["daily"] == {"period": "2026-11-10", "tasks": {}}

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers=headers,
            json={"events": [CARD]},
        )
        assert response.json()["granted_rewards"] == []
        assert response.json()["user_resources"] is None
        assert response.json()["user_achievements"] == response_json["user_achievements"]

        assert await db_connection.fetchval("SELECT money FROM user_resources WHERE id = $1", user_id) == 120

    @pytest.mark.asyncio
    async def test_sum_and_unmatched_events(
        self,
        # service fixtures
        client: AsyncClient,
        # fixtures for test
        achievements_setup,
    ):
        user_id, headers = achievements_setup

        events = [
            {"type": "action.played", "data": {"actor": {"id": 7}}},
            {"type": "action.played", "data": {"actor": {"faction": "Neutral", "id": 2, "color": "Silver"}}},
            {"type": "resource.spent", "data": {"resource": "money", "amount": 40.5}},
            {"type": "resource.spent", "data": {"resource": "money", "amount": 60}},
        ]

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers=headers,
            json={"events": events},
        )

        assert response.status_code == 200

        response_json = response.json()
        assert set(response_json["user_achievements"]["permanent"]) == {"spend_100"}
        assert response_json["user_achievements"]["permanent"]["spend_100"]["value"] == 100
        assert response_json["user_resources"]["money"] == 110  # resource.spent does not debit the balance.

    @pytest.mark.parametrize(
        "invalid",
        [
            {"type": "unknown", "data": {}},
            {"type": "action.played", "data": {}},
            {"type": "action.played", "data": {"actor": []}},
            {"type": "action.played", "data": {"actor": None}},
            {"type": "resource.spent", "data": {"resource": "unknown", "amount": 1}},
            {"type": "resource.spent", "data": {"resource": "money", "amount": -1}},
            {"type": "resource.spent", "data": {"resource": "money", "amount": "10"}},
            {"type": "resource.spent", "data": {"resource": "money", "amount": True}},
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_batch_is_rejected(
        self,
        # service fixtures
        client: AsyncClient,
        db_connection,
        # fixtures for test
        achievements_setup,
        invalid,
    ):
        user_id, headers = achievements_setup

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers=headers,
            json={"events": [CARD, CARD, invalid]},
        )

        assert response.status_code == 422

        assert await db_connection.fetchval("SELECT progress FROM user_achievements WHERE id = $1", user_id) is None

        assert await db_connection.fetchval("SELECT money FROM user_resources WHERE id = $1", user_id) == 100

    @pytest.mark.asyncio
    async def test_concurrent_completion(
        self,
        # service fixtures
        app,
        app_config,
        db_connection,
        # fixtures for test
        achievements_setup,
    ):
        user_id, _ = achievements_setup
        service = AchievementsService(await get_db(), app_config)
        events = AchievementEventsRequest.model_validate({"events": [CARD, CARD, CARD]}).events

        responses = await asyncio.gather(
            service.process_events(user_id, events),
            service.process_events(user_id, events),
        )

        assert sum(len(response.granted_rewards) for response in responses) == 2

        assert await db_connection.fetchval("SELECT money FROM user_resources WHERE id = $1", user_id) == 120

    @pytest.mark.asyncio
    async def test_reward_failure_rolls_back(
        self,
        # service fixtures
        app,
        app_config,
        db_connection,
        # fixtures for test
        achievements_setup,
    ):
        user_id, _ = achievements_setup
        service = AchievementsService(await get_db(), app_config)
        events = AchievementEventsRequest.model_validate({"events": [CARD, CARD, CARD]}).events

        calls = 0

        async def fail_second_reward(**kwargs) -> UserResources:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("Reward failure")
            return await change_resources(**kwargs)

        with (
            patch(
                "services.api.app.apps.user_achievements.service.progress_logic.change_resources",
                side_effect=fail_second_reward,
            ),
            pytest.raises(RuntimeError, match="Reward failure"),
        ):
            await service.process_events(user_id, events)

        assert await db_connection.fetchval("SELECT progress FROM user_achievements WHERE id = $1", user_id) is None

        assert await db_connection.fetchval("SELECT money FROM user_resources WHERE id = $1", user_id) == 100
