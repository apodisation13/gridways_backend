import pytest

from httpx import AsyncClient


class TestUsersAPI:
    """Асинхронные тесты для эндпоинта /accounts"""

    @pytest.mark.asyncio
    async def test_get_users_empty_1(
        self,
        client: AsyncClient,
        db_connection,
        event_sender_mock,
    ) -> None:
        a = await db_connection.fetch("SELECT * FROM users")
        print("STR20", a)

        response = await client.get("/users/list-users")

        assert response.status_code == 200
        assert response.json() == []

        print(event_sender_mock.call_args_list)

    @pytest.mark.asyncio
    async def test_get_users_empty(
        self,
        client: AsyncClient,
        db_connection,
        user_factory,
        init_db_cards,
    ) -> None:
        a = await db_connection.fetch("SELECT * FROM card_decks")
        print("STR40", a)

        user = await user_factory(
            # email="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            is_active=False,
        )
        print("STR35", type(user), user.id, user.is_active)

        response = await client.post(
            "/users/register-user",
            json={
                "email": "email",
                "password": "password",
                "username": "username",
            }
        )

        a = await db_connection.fetch("SELECT * FROM users")
        print("STR40", a)

        response_json = response.json()
        print("STR38", response_json)
        assert response.status_code == 200

        response = await client.post(
            "/users/login-user",
            json={
                "email": "email",
                "password": "password",
            }
        )

        response_json = response.json()
        print("STR38", response_json)
        assert response.status_code == 200

        token = response_json["token"]["access_token"]
        print(58, token)

        response = await client.get(
            "/user-progress/1",
            headers={"Authorization": f"Bearer {token}"},
        )
        response_json = response.json()
        print("STR38", response_json)
