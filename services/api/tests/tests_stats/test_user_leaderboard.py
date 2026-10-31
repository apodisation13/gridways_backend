from datetime import datetime, timedelta

import pytest

from httpx import AsyncClient
from lib.utils.schemas.game import LeaderboardGameMode


@pytest.mark.asyncio
class TestUserLeaderboardAPI:
    endpoint = "statistics/{user_id}/leaderboard"

    @pytest.mark.usefixtures("init_db_cards")
    async def test_get_leaderboard(
        self,
        # service fixtures
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        leaderboard_factory,
        leader_factory,
    ):
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        # -------------- 1й запрос - юзер еще не играл --------------
        response = await client.get(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_json = response.json()
        assert response.status_code == 200

        assert response_json == []

        l2 = await leader_factory(
            faction_id=1,  # Neutral
            ability_id=1,
        )

        # сыграли несколько игр
        await leaderboard_factory(
            user_id=user_id,
            leader_id=1,
            max_kills=7,
            mode=LeaderboardGameMode.SEASON,
        )
        await leaderboard_factory(
            user_id=user_id,
            leader_id=1,
            max_kills=17,
            mode=LeaderboardGameMode.RANDOM,
        )
        await leaderboard_factory(
            user_id=user_id,
            leader_id=l2.id,
            max_kills=17,
            mode=LeaderboardGameMode.SEASON,
        )

        # -------------- 2й запрос - после нескольких игр --------------
        response = await client.get(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_json = response.json()
        assert response.status_code == 200

        assert response_json == [
            {
                "user_id": user_id,
                "username": "username",
                "user_avatar": None,
                "max_kills": 17,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.SEASON,
                "leader_id": l2.id,
                "faction_name": "Neutral",
            },
            {
                "user_id": user_id,
                "username": "username",
                "user_avatar": None,
                "max_kills": 17,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.RANDOM,
                "leader_id": 1,
                "faction_name": "Soldiers",
            },
            {
                "user_id": user_id,
                "username": "username",
                "user_avatar": None,
                "max_kills": 7,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.SEASON,
                "leader_id": 1,
                "faction_name": "Soldiers",
            },
        ]

    @pytest.mark.usefixtures("init_db_cards")
    async def test_post_leaderboard(
        self,
        # service fixtures
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        user_deck_factory,
        leader_factory,
        deck_factory,
    ):
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        user_deck = await user_deck_factory(
            user_id=user_id,
            deck_id=1,
        )

        # -------------- 1й запрос - играем 1ю игру --------------
        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "user_deck_id": user_deck.id,
                "max_kills": 21,
                "mode": LeaderboardGameMode.RANDOM,
            },
        )

        response_json = response.json()
        assert response.status_code == 200

        assert response_json == {"200": "OK"}

        # -------------- 2й запрос - играем 2ю игру, но перебили меньше --------------
        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "user_deck_id": user_deck.id,
                "max_kills": 17,
                "mode": LeaderboardGameMode.RANDOM,
            },
        )

        response_json = response.json()
        assert response.status_code == 200

        assert response_json == {"200": "OK"}

        # -------------- 3й запрос - играем 3ю игру, перебили больше! --------------
        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "user_deck_id": user_deck.id,
                "max_kills": 27,
                "mode": LeaderboardGameMode.RANDOM,
            },
        )

        response_json = response.json()
        assert response.status_code == 200

        assert response_json == {"200": "OK"}

        # -------------- 4й запрос - другой режим --------------
        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "user_deck_id": user_deck.id,
                "max_kills": 8,
                "mode": LeaderboardGameMode.SEASON,
            },
        )

        response_json = response.json()
        assert response.status_code == 200

        assert response_json == {"200": "OK"}

        # другая фракция
        l2 = await leader_factory(
            faction_id=1,  # Neutral
            ability_id=1,
        )
        new_deck = await deck_factory(
            name="new-deck",
            leader_id=l2.id,
        )
        new_user_deck = await user_deck_factory(
            user_id=user_id,
            deck_id=new_deck.id,
        )

        # -------------- 5й запрос - другая фракция --------------
        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "user_deck_id": new_user_deck.id,
                "max_kills": 12,
                "mode": LeaderboardGameMode.RANDOM,
            },
        )

        response_json = response.json()
        assert response.status_code == 200

        assert response_json == {"200": "OK"}

        # ------------------------- а теперь идем и берем доску лидеров -------------------------
        response = await client.get(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_json = response.json()
        assert response.status_code == 200

        assert response_json == [
            {
                "user_id": user_id,
                "username": "username",
                "user_avatar": None,
                "max_kills": 27,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.RANDOM,
                "leader_id": 1,
                "faction_name": "Soldiers",
            },
            {
                "user_id": user_id,
                "username": "username",
                "user_avatar": None,
                "max_kills": 12,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.RANDOM,
                "leader_id": l2.id,
                "faction_name": "Neutral",
            },
            {
                "user_id": user_id,
                "username": "username",
                "user_avatar": None,
                "max_kills": 8,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.SEASON,
                "leader_id": 1,
                "faction_name": "Soldiers",
            },
        ]

    @pytest.mark.usefixtures("init_db_cards")
    async def test_post_arena_leaderboard(
        self,
        client: AsyncClient,
        user_login_fixture,
        user_deck_factory,
        db_connection,
    ):
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]
        user_deck = await user_deck_factory(user_id=user_id, deck_id=1)
        previous = None

        for result, expected in [
            ({"max_kills": 43}, (43, 0)),
            ({"max_kills": 43, "max_arena_level": 6}, (43, 6)),
            ({"max_kills": 40, "max_arena_level": 7}, (43, 7)),
            ({"max_kills": 50, "max_arena_level": 5}, (50, 7)),
            ({"max_kills": 50, "max_arena_level": 7}, (50, 7)),
            ({"max_kills": 40, "max_arena_level": 5}, (50, 7)),
            ({"max_kills": 51}, (51, 7)),
            ({"max_kills": 52, "max_arena_level": None}, (52, 7)),
            ({"max_kills": 60, "max_arena_level": 8}, (60, 8)),
        ]:
            payload = {
                "user_deck_id": user_deck.id,
                "mode": LeaderboardGameMode.ARENA,
            }
            payload.update(result)
            response = await client.post(
                self.endpoint.format(user_id=user_id),
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            )
            assert response.status_code == 200
            rows = await db_connection.fetch(
                "SELECT * FROM leaderboard WHERE user_id = $1 AND mode = $2",
                user_id,
                LeaderboardGameMode.ARENA,
            )
            assert len(rows) == 1
            current = rows[0]
            assert (current["max_kills"], current["max_arena_level"]) == expected
            if previous is not None:
                assert current["id"] == previous["id"]
                if (previous["max_kills"], previous["max_arena_level"]) == expected:
                    assert current["updated_at"] == previous["updated_at"]
            previous = current


@pytest.mark.asyncio
class TestWorldLeaderboardAPI:
    endpoint = "statistics/{user_id}/leaderboard-world"

    @pytest.mark.usefixtures("init_db_cards")
    async def test_get_leaderboard_world(
        self,
        # service fixtures
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        leaderboard_factory,
        user_factory,
        user_preferences_factory,
    ):
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        time_now = datetime.now()

        # -------------- 1й запрос - юзер еще не играл --------------
        response = await client.get(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

        # сыграли несколько игр
        await leaderboard_factory(
            user_id=user_id,
            leader_id=1,
            max_kills=7,
            mode=LeaderboardGameMode.SEASON,
            updated_at=time_now - timedelta(hours=11),
        )
        await leaderboard_factory(
            user_id=user_id,
            leader_id=1,
            max_kills=17,
            mode=LeaderboardGameMode.RANDOM,
            updated_at=time_now - timedelta(hours=10),
        )

        user_2 = await user_factory(username="user_2")
        await leaderboard_factory(
            user_id=user_2.id,
            leader_id=1,
            max_kills=17,
            mode=LeaderboardGameMode.SEASON,
            updated_at=time_now - timedelta(hours=9),
        )

        user_3 = await user_factory(username="user_3")
        await user_preferences_factory(
            id=user_3.id,
            data={"avatar": "some_avatar"},
        )
        await leaderboard_factory(
            user_id=user_3.id,
            leader_id=1,
            max_kills=7,
            mode=LeaderboardGameMode.SEASON,
            updated_at=time_now - timedelta(hours=3),
        )
        await leaderboard_factory(
            user_id=user_3.id,
            leader_id=1,
            max_kills=16,
            mode=LeaderboardGameMode.RANDOM_N,
        )

        # -------------- 2й запрос - после нескольких игр --------------
        response = await client.get(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_json = response.json()
        assert response.status_code == 200

        assert len(response_json) == 5

        assert response_json == [
            {
                "user_id": user_2.id,
                "username": "user_2",
                "user_avatar": None,
                "max_kills": 17,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.SEASON,
                "leader_id": 1,
                "faction_name": "Soldiers",
            },
            {
                "user_id": user_id,
                "username": "username",
                "user_avatar": None,
                "max_kills": 17,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.RANDOM,
                "leader_id": 1,
                "faction_name": "Soldiers",
            },
            {
                "user_id": user_3.id,
                "username": "user_3",
                "user_avatar": "some_avatar",
                "max_kills": 16,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.RANDOM_N,
                "leader_id": 1,
                "faction_name": "Soldiers",
            },
            {
                "user_id": user_3.id,
                "username": "user_3",
                "user_avatar": "some_avatar",
                "max_kills": 7,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.SEASON,
                "leader_id": 1,
                "faction_name": "Soldiers",
            },
            {
                "user_id": user_id,
                "username": "username",
                "user_avatar": None,
                "max_kills": 7,
                "max_arena_level": 0,
                "mode": LeaderboardGameMode.SEASON,
                "leader_id": 1,
                "faction_name": "Soldiers",
            },
        ]
