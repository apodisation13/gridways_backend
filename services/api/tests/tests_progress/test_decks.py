import pytest

from httpx import AsyncClient


# Небольшие колоды для тестов: уровень 0 разрешает 2 карты, уровень 6 — 3.
# Уровни апгрейдов и разрешённое количество намеренно различаются.
DECK_GAME_CONSTANTS = {
    "upgrades": {
        "game": {
            "upgrades": {
                "max_cards_in_deck": {"upgrades": {"0": {"value": 2}, "6": {"value": 3}}},
                "max_decks": {"upgrades": {"0": {"value": 2}, "2": {"value": 5}}},
            },
        },
    },
}


@pytest.mark.usefixtures("init_db_cards")
@pytest.mark.parametrize("init_db_cards", [DECK_GAME_CONSTANTS], indirect=True)
class TestCreateDeckAPI:
    endpoint = "user-progress/{user_id}/create-deck"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("cards", "expected_cards", "expected_health"),
        [
            ([1, 2], [2, 1], 31),
            ([1, 2, 3], [3, 2, 1], 42),
        ],
    )
    async def test_create_deck_success(
        self,
        cards,
        expected_cards,
        expected_health,
        # service fixtures
        client: AsyncClient,
        db_connection,
        user_login_fixture,
        # fixtures for test
        user_deck_factory,
        user_card_factory,
        user_leader_factory,
        user_upgrades_factory,
    ):
        user_id = user_login_fixture["id"]

        # у юзера уровень апгрейда - 6, в тесте это соответствует 3 картам в колоде (а 0й уровень - 2 карты)
        await user_upgrades_factory(
            id=user_id,
            data={"game": {"max_cards_in_deck": 6, "max_decks": 0}},
        )
        # открываем для юзера лидера и карты
        await user_leader_factory(user_id=user_id, leader_id=1)
        await user_card_factory(user_id=user_id, card_id=1)
        await user_card_factory(user_id=user_id, card_id=2)
        await user_card_factory(user_id=user_id, card_id=3)
        # и базовую колоду тоже
        base_deck = await user_deck_factory(user_id=user_id, deck_id=1)

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {user_login_fixture['token']['access_token']}"},
            json={"deck_name": "Новая колода", "leader_id": 1, "cards": cards},
        )

        assert response.status_code == 200

        response_json = response.json()

        # init_db_cards: 1 — бронзовая, 2 — серебряная, 3 — золотая.
        # Цвет сортируется по убыванию: [2, 1] либо [3, 2, 1].
        # Здоровье: 10 у лидера + 10/11/11 у выбранных карт.
        assert response_json == {
            "decks": [
                {
                    "user_deck_id": 2,  # тут так можно, id=1 у базовой, id=2 у новой
                    "deck": {
                        "id": 2,  # тут так можно, ибо других колод нету
                        "name": "Новая колода",
                        "leader_id": 1,
                        "cards": expected_cards,
                        "health": expected_health,
                    },
                },
                {
                    "user_deck_id": base_deck.id,
                    "deck": {"id": 1, "name": "base-deck", "leader_id": 1, "cards": [3, 2, 1], "health": 42},
                },
            ],
        }

        decks = await db_connection.fetch("""SELECT * FROM decks ORDER BY updated_at DESC""")
        assert len(decks) == 2  # базовая + новая
        assert decks[0]["name"] == "Новая колода"
        assert decks[0]["leader_id"] == 1

        relations = await db_connection.fetch("""SELECT * FROM user_decks ORDER BY updated_at DESC""")
        assert len(relations) == 2  # и опять же - базовая + новая
        assert relations[0]["user_id"] == user_id
        assert relations[1]["user_id"] == user_id

        card_decks = await db_connection.fetch("""SELECT * FROM card_decks""")
        assert len(card_decks) == 3 + len(expected_cards)  # 3 было в базовой + добавились новые

    @pytest.mark.asyncio
    async def test_duplicate_cards(
        self,
        # service fixtures
        client: AsyncClient,
        db_connection,
        user_login_fixture,
    ):
        user_id = user_login_fixture["id"]

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {user_login_fixture['token']['access_token']}"},
            json={"deck_name": "Дубли карт", "leader_id": 1, "cards": [1, 1]},
        )

        assert response.status_code == 400
        assert response.json()["error"]["message"] == "A deck cannot contain duplicate cards"

        assert await db_connection.fetchval("""SELECT COUNT(*) FROM decks""") == 1  # новых не добавилось

    @pytest.mark.asyncio
    @pytest.mark.parametrize("count", [None, 0, -1])
    async def test_locked_leader(
        self,
        count,
        # service fixtures
        client: AsyncClient,
        db_connection,
        user_login_fixture,
        # fixtures for test
        user_leader_factory,
        user_factory,
    ):
        # Колоду с закрытым лидером нельзя создать
        # (если записи нет вообще, если там count 0 или вдруг меньше 0)
        user_id = user_login_fixture["id"]
        token = user_login_fixture["token"]["access_token"]

        if count is not None:
            await user_leader_factory(user_id=user_id, leader_id=1, count=count)

        # Открытый лидер другого пользователя - если что - не даёт доступа текущему
        other_user = await user_factory()
        await user_leader_factory(user_id=other_user.id, leader_id=1)

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {token}"},
            json={"deck_name": "Закрытый лидер", "leader_id": 1, "cards": [1, 2]},
        )

        assert response.status_code == 400
        assert response.json()["error"]["message"] == "The selected leader is not unlocked"

        assert await db_connection.fetchval("""SELECT COUNT(*) FROM decks""") == 1  # новых не добавилось

    @pytest.mark.asyncio
    @pytest.mark.parametrize("count", [None, 0, -1])
    async def test_locked_card(
        self,
        count,
        # service fixtures
        client: AsyncClient,
        db_connection,
        user_login_fixture,
        # fixtures for test
        user_card_factory,
        user_leader_factory,
        user_factory,
    ):
        user_id = user_login_fixture["id"]
        token = user_login_fixture["token"]["access_token"]

        await user_leader_factory(user_id=user_id, leader_id=1)
        await user_card_factory(user_id=user_id, card_id=1)

        if count is not None:
            await user_card_factory(user_id=user_id, card_id=2, count=count)

        # Карты другого юзера тут роли не играют
        other_user = await user_factory()
        await user_card_factory(user_id=other_user.id, card_id=2)

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {token}"},
            json={"deck_name": "Закрытая карта", "leader_id": 1, "cards": [1, 2]},
        )

        assert response.status_code == 400
        assert response.json()["error"]["message"] == "Cards are not unlocked: {2}"

        assert await db_connection.fetchval("""SELECT COUNT(*) FROM decks""") == 1  # новых не добавилось

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("level", "cards", "status"),
        [
            (0, [], 400),
            (0, [1], 400),
            (0, [1, 2], 200),
            (0, [1, 2, 3], 400),
            (6, [1], 400),
            (6, [1, 2], 200),
            (6, [1, 2, 3], 200),
            (6, [1, 2, 3, 4], 400),
        ],
    )
    async def test_deck_size_upgrade_bounds(
        self,
        level,
        cards,
        status,
        # service fixtures
        client: AsyncClient,
        db_connection,
        user_login_fixture,
        # fixtures for test
        user_upgrades_factory,
        user_card_factory,
        user_leader_factory,
        card_factory,
    ):
        user_id = user_login_fixture["id"]
        token = user_login_fixture["token"]["access_token"]

        await user_upgrades_factory(
            id=user_id,
            data={"game": {"max_cards_in_deck": level, "max_decks": 0}},
        )

        await user_leader_factory(user_id=user_id, leader_id=1)

        await card_factory(id=4, faction_id=1, color_id=1, type_id=1, ability_id=1, data={"hp": 10})

        for card_id in (1, 2, 3, 4):
            await user_card_factory(user_id=user_id, card_id=card_id)

        # В DECK_GAME_CONSTANTS: минимум 2, максимум 2 на уровне 0 - и 3 на уровне 6
        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {token}"},
            json={"deck_name": "Проверка длины", "leader_id": 1, "cards": cards},
        )

        assert response.status_code == status
        if status == 400:
            maximum = 2 if level == 0 else 3
            assert response.json()["error"]["message"] == f"Deck size must be between 2 and {maximum} cards"
        else:
            assert response.json()["decks"][0]["deck"]["cards"] == list(reversed(cards))

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("cards", "expected_status"),
        [
            ([1, 2], 200),
            ([1, 2, 3], 400),
        ],
    )
    async def test_deck_size_no_upgrade_at_all(
        self,
        cards,
        expected_status,
        # service fixtures
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        user_card_factory,
        user_leader_factory,
    ):
        # при отсутствии апгрейда просто возьмется первый уровень прокачки - по тесту это 2 карты
        user_id = user_login_fixture["id"]
        token = user_login_fixture["token"]["access_token"]

        await user_leader_factory(user_id=user_id, leader_id=1)

        for card_id in (1, 2, 3):
            await user_card_factory(user_id=user_id, card_id=card_id)

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {token}"},
            json={"deck_name": "Проверка длины без апгрейда", "leader_id": 1, "cards": cards},
        )

        assert response.status_code == expected_status

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("level", "capacity"), [(0, 2), (2, 5)])
    async def test_max_decks_upgrade(
        self,
        level,
        capacity,
        # service fixtures
        client: AsyncClient,
        db_connection,
        user_login_fixture,
        # fixtures for test
        user_factory,
        user_deck_factory,
        deck_factory,
        user_card_factory,
        user_leader_factory,
        user_upgrades_factory,
    ):
        user_id = user_login_fixture["id"]

        await user_upgrades_factory(
            id=user_id,
            data={"game": {"max_cards_in_deck": 6, "max_decks": level}},
        )
        await user_leader_factory(user_id=user_id, leader_id=1)

        for card_id in (1, 2, 3):
            await user_card_factory(user_id=user_id, card_id=card_id)

        token = user_login_fixture["token"]["access_token"]

        # Базовая колода пользователя уже занимает один слот
        await user_deck_factory(user_id=user_id, deck_id=1)

        # Колоды другого пользователя не занимают наши слоты
        other = await user_factory()
        other_deck = await deck_factory(leader_id=1)
        await user_deck_factory(user_id=other.id, deck_id=other_deck.id)

        # Создать можно только оставшиеся capacity - 1 колод
        for _ in range(capacity - 1):
            response = await client.post(
                self.endpoint.format(user_id=user_id),
                headers={"Authorization": f"Bearer {token}"},
                json={"deck_name": "Колода", "leader_id": 1, "cards": [1, 2]},
            )
            assert response.status_code == 200

        all_decks_count = await db_connection.fetchval("""SELECT COUNT(*) FROM decks""")
        assert all_decks_count == 1 + 1 + (capacity - 1)  # базовая + другого юзера + сколько нужно нашего юзера

        user_decks_count = await db_connection.fetchval(
            """SELECT COUNT(*) FROM user_decks WHERE user_id = $1""",
            user_id,
        )
        assert user_decks_count == capacity - 1 + 1  # создалось capacity - 1 и + 1 еще базовая

        response = await client.post(
            self.endpoint.format(user_id=user_id),
            headers={"Authorization": f"Bearer {token}"},
            json={"deck_name": "Лишняя колода", "leader_id": 1, "cards": [1, 2]},
        )
        assert response.status_code == 400
        assert response.json()["error"]["message"] == f"Maximum number of decks reached: {capacity}"

        # после ошибочного запроса уже ничего не поменялось
        all_decks_count = await db_connection.fetchval("""SELECT COUNT(*) FROM decks""")
        assert all_decks_count == 1 + 1 + (capacity - 1)
        user_decks_count = await db_connection.fetchval(
            """SELECT COUNT(*) FROM user_decks WHERE user_id = $1""",
            user_id,
        )
        assert user_decks_count == capacity - 1 + 1


@pytest.mark.usefixtures("init_db_cards")
@pytest.mark.parametrize("init_db_cards", [DECK_GAME_CONSTANTS], indirect=True)
class TestPatchDeckAPI:
    endpoint = "user-progress/{user_id}/alter-deck/{deck_id}"

    @pytest.mark.asyncio
    async def test_patch_deck_success(
        self,
        # service fixtures
        client: AsyncClient,
        db_connection,
        user_login_fixture,
        # fixtures for test
        user_deck_factory,
        deck_factory,
        card_deck_factory,
        leader_factory,
        user_leader_factory,
        user_card_factory,
        user_upgrades_factory,
    ):
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        await user_upgrades_factory(
            id=user_id,
            data={"game": {"max_cards_in_deck": 6, "max_decks": 0}},
        )
        await user_leader_factory(user_id=user_id, leader_id=1)

        for card_id in (1, 2, 3):
            await user_card_factory(user_id=user_id, card_id=card_id)

        base_deck = await user_deck_factory(user_id=user_id, deck_id=1)

        second_deck = await deck_factory(name="Вторая колода", leader_id=1)
        second_user_deck = await user_deck_factory(user_id=user_id, deck_id=second_deck.id)
        await card_deck_factory(deck_id=second_deck.id, card_id=1)
        await card_deck_factory(deck_id=second_deck.id, card_id=2)
        await card_deck_factory(deck_id=second_deck.id, card_id=3)

        # будем менять на этого лидера
        new_leader = await leader_factory(faction_id=2, ability_id=1, data={"hp": 50})
        await user_leader_factory(user_id=user_id, leader_id=new_leader.id, count=1)

        response = await client.patch(
            self.endpoint.format(user_id=user_id, deck_id=second_deck.id),
            headers={"Authorization": f"Bearer {access_token}"},
            json={"deck_name": "Изменённая колода", "leader_id": new_leader.id, "cards": [2, 3]},
        )

        assert response.status_code == 200
        assert response.json() == {
            "decks": [
                {
                    "user_deck_id": second_user_deck.id,
                    "deck": {
                        "id": 2,
                        "name": "Изменённая колода",
                        "leader_id": new_leader.id,
                        "cards": [3, 2],
                        "health": 72,
                    },
                },
                {
                    "user_deck_id": base_deck.id,
                    "deck": {"id": 1, "name": "base-deck", "leader_id": 1, "cards": [3, 2, 1], "health": 42},
                },
            ],
        }

        decks = await db_connection.fetch("""SELECT name, leader_id FROM decks ORDER BY updated_at DESC""")
        assert len(decks) == 2
        assert dict(decks[0]) == {"name": "Изменённая колода", "leader_id": new_leader.id}

        card_decks = await db_connection.fetch("""SELECT card_id FROM card_decks""")
        assert len(card_decks) == 3 + 2  # три по-прежнему от базовой колоды и две от измененной, а 2 удалились

        user_decks = await db_connection.fetch("""SELECT * FROM user_decks""")
        assert len(user_decks) == 2


@pytest.mark.usefixtures("init_db_cards")
class TestDeleteDeckAPI:
    endpoint = "user-progress/{user_id}/alter-deck/{deck_id}"

    @pytest.mark.asyncio
    async def test_delete_deck_success(
        self,
        # service fixtures
        client: AsyncClient,
        db_connection,
        user_login_fixture,
        # fixtures for test
        user_deck_factory,
        deck_factory,
        card_deck_factory,
    ):
        user_id = user_login_fixture["id"]
        token = user_login_fixture["token"]["access_token"]

        # У пользователя три колоды: базовая, вторая и третья
        base_user_deck = await user_deck_factory(user_id=user_id, deck_id=1)

        second_deck = await deck_factory(name="Вторая колода", leader_id=1)
        second_user_deck = await user_deck_factory(user_id=user_id, deck_id=second_deck.id)
        await card_deck_factory(deck_id=second_deck.id, card_id=1)
        await card_deck_factory(deck_id=second_deck.id, card_id=2)

        third_deck = await deck_factory(name="Третья колода", leader_id=1)
        await user_deck_factory(user_id=user_id, deck_id=third_deck.id)
        await card_deck_factory(deck_id=third_deck.id, card_id=2)
        await card_deck_factory(deck_id=third_deck.id, card_id=3)

        # Удаляем третью деку
        response = await client.delete(
            self.endpoint.format(user_id=user_id, deck_id=third_deck.id),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

        # После удаления третьей остаются вторая и базовая, по updated_at DESC
        assert response.json() == {
            "decks": [
                {
                    "user_deck_id": second_user_deck.id,
                    "deck": {
                        "id": second_deck.id,
                        "name": "Вторая колода",
                        "leader_id": 1,
                        "cards": [2, 1],
                        "health": 31,
                    },
                },
                {
                    "user_deck_id": base_user_deck.id,
                    "deck": {"id": 1, "name": "base-deck", "leader_id": 1, "cards": [3, 2, 1], "health": 42},
                },
            ],
        }

        decks = await db_connection.fetch("""SELECT id FROM decks""")
        assert len(decks) == 2

        user_decks = await db_connection.fetch("""SELECT user_id, deck_id FROM user_decks""")
        assert len(user_decks) == 2

        # Связи удалённой колоды исчезли
        cards_decks = await db_connection.fetch("""SELECT * FROM card_decks WHERE deck_id = $1""", third_deck.id)
        assert len(cards_decks) == 0

    @pytest.mark.asyncio
    async def test_delete_base_deck_forbidden(
        self,
        # service fixtures
        client: AsyncClient,
        db_connection,
        user_login_fixture,
        # fixtures for test
        user_deck_factory,
    ):
        user_id = user_login_fixture["id"]
        token = user_login_fixture["token"]["access_token"]

        # Базовая колода принадлежит пользователю, но удалять её всё равно нельзя
        await user_deck_factory(user_id=user_id, deck_id=1)

        response = await client.delete(
            self.endpoint.format(user_id=user_id, deck_id=1),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert response.json()["error"]["message"] == "The base deck cannot be deleted"

        decks = await db_connection.fetch("""SELECT * FROM decks""")
        assert len(decks) == 1
        user_decks = await db_connection.fetch("""SELECT * FROM user_decks""")
        assert len(user_decks) == 1

    @pytest.mark.asyncio
    async def test_delete_another_users_deck(
        self,
        # service fixtures
        client: AsyncClient,
        db_connection,
        user_login_fixture,
        # fixtures for test
        user_factory,
        user_deck_factory,
        deck_factory,
        card_deck_factory,
    ):
        user_id = user_login_fixture["id"]
        token = user_login_fixture["token"]["access_token"]
        await user_deck_factory(user_id=user_id, deck_id=1)

        other_user = await user_factory()
        other_deck = await deck_factory(name="Чужая колода", leader_id=1)
        await user_deck_factory(user_id=other_user.id, deck_id=other_deck.id)
        await card_deck_factory(deck_id=other_deck.id, card_id=1)
        await card_deck_factory(deck_id=other_deck.id, card_id=2)

        # наш юзер пытается удалить чужую колоду
        response = await client.delete(
            self.endpoint.format(user_id=user_id, deck_id=other_deck.id),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert response.json()["error"]["message"] == "Deck does not exist or does not belong to the user"

        # тут как было, так и осталось
        decks = await db_connection.fetch("""SELECT * FROM decks""")
        assert len(decks) == 2
        user_decks = await db_connection.fetch("""SELECT * FROM user_decks""")
        assert len(user_decks) == 2
