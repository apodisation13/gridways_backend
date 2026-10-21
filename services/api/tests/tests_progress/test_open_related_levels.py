import pytest

from httpx import AsyncClient
from lib.utils.schemas.game import ResourceType


class TestOpenRelatedLevelsAPI:
    endpoint = "user-progress/{user_id}/open-related-levels/{user_level_id}"

    @pytest.mark.parametrize("level_finished", [True, False])
    @pytest.mark.usefixtures("init_db_cards")
    @pytest.mark.asyncio
    async def test_open_level_without_related_levels(
        self,
        level_finished: bool,
        # service fixtures
        db_connection,
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        level_factory,
        level_enemy_factory,
        user_level_factory,
        user_season_factory,
    ):
        """
        Базовая фикстура добавила уже 4 разных уровня
        У юзера открыт уровень id=5, который мы создали в этом тесте
        У этого уровня нет связанных уровней (level_related_levels)
        Соответственно если юзер проходит этот уровень, то ему мы поставим finished
        И всё, открывать новые не надо, их ведь нет
        Если уровень УЖЕ пройден, ничего страшного, так и останется
        """
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        level = await level_factory(
            season_id=1,
            enemy_leader_id=1,
        )
        # чтобы ручка корректно вернула, что этот уровень есть вообще, по коду стоит JOIN level_enemies
        await level_enemy_factory(
            level_id=level.id,
            enemy_id=1,
        )

        user_level = await user_level_factory(
            user_id=user_id,
            level_id=level.id,
            finished=level_finished,
        )
        await user_season_factory(
            user_id=user_id,
            season_id=1,
        )

        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=user_level.id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        response_json = response.json()

        # теперь ручка возвращает только список открытых/пройденных уровней ЮЗЕРА, а не все
        levels: dict = response_json["seasons"]["1"]["levels"]
        assert levels == {
            str(level.id): {
                "user_level_id": user_level.id,
                "finished": True,
            },
        }

        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels""")
        assert len(user_levels) == 1
        assert user_levels[0]["finished"] is True  # вот это самое главное - уровню поставилось что он пройден

    @pytest.mark.usefixtures("init_db_cards")
    @pytest.mark.asyncio
    async def test_open_level_with_related_levels(
        self,
        # service fixtures
        db_connection,
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        user_level_factory,
        user_season_factory,
    ):
        """
        Базовая фикстура добавила уже 3 разных уровня, и там у уровня 1 есть связанные: 2 и 3
        Соответственно если юзер проходит этот уровень, то ему мы поставим finished
        А уровни 2 и 3 - станут unlocked для юзера
        Если исходный уровень УЖЕ пройден, ничего страшного, так и останется (2й запрос)
        """
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        await user_season_factory(
            user_id=user_id,
            season_id=1,
        )

        # 1й уровень открыт у юзера, но еще не пройден
        user_level = await user_level_factory(
            user_id=user_id,
            level_id=1,
            finished=False,
        )

        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels""")
        assert len(user_levels) == 1
        assert user_levels[0]["finished"] is False

        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=user_level.id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        response_json = response.json()

        levels = response_json["seasons"]["1"]["levels"]
        assert levels == {
            "1": {
                "user_level_id": user_level.id,
                "finished": True,
            },
            "2": {
                "user_level_id": 2,
                "finished": False,
            },
            "3": {
                "user_level_id": 3,
                "finished": False,
            },
        }

        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels ORDER BY updated_at""")

        # а вот тут важно: был 1 уровень, он стал пройденным, а 2 новых открылись!
        assert len(user_levels) == 3

        assert user_levels[0]["finished"] is True  # вот это самое главное - 1му уровню поставилось что он пройден

        # а эти стали открыты, но не пройдены
        assert user_levels[1]["finished"] is False
        assert user_levels[2]["finished"] is False

        # --------------- повторный запрос на тот же уже пройденный уровень ---------------
        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=user_level.id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        response_json = response.json()

        levels = response_json["seasons"]["1"]["levels"]
        assert levels == {
            "1": {
                "user_level_id": user_level.id,
                "finished": True,
            },
            "2": {
                "user_level_id": 2,
                "finished": False,
            },
            "3": {
                "user_level_id": 3,
                "finished": False,
            },
        }

        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels ORDER BY updated_at""")

        assert len(user_levels) == 3

        # они здесь не изменились
        assert user_levels[0]["finished"] is True
        assert user_levels[1]["finished"] is False
        assert user_levels[2]["finished"] is False

        # --------------- а теперь проходит еще 2й уровень ---------------
        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=2),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        response_json = response.json()

        levels = response_json["seasons"]["1"]["levels"]
        assert levels == {
            "1": {
                "user_level_id": user_level.id,
                "finished": True,
            },
            "2": {
                "user_level_id": 2,
                "finished": True,  # <- вот тут теперь стало True
            },
            "3": {
                "user_level_id": 3,
                "finished": False,
            },
        }

        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels ORDER BY updated_at DESC""")

        assert len(user_levels) == 3

        # уровень 2 изменился самым первым, в списке последний
        assert user_levels[0]["id"] == 2
        assert user_levels[0]["finished"] is True

        # это 1й уровень, он как был, так и остался
        assert user_levels[1]["id"] == 1
        assert user_levels[1]["finished"] is True

        # ничего не изменилось с 3м уровнем! он все еще не пройден (но открыт, так как вообще есть в user_levels)
        assert user_levels[2]["id"] == 3
        assert user_levels[2]["finished"] is False

    @pytest.mark.usefixtures("init_db_cards")
    @pytest.mark.asyncio
    async def test_open_level_related_levels_already_open(
        self,
        # service fixtures
        db_connection,
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        user_level_factory,
        user_season_factory,
    ):
        """
        Базовая фикстура добавила уже 3 разных уровня, и там у уровня 1 есть связанные: 2 и 3
        Пусть у юзера уже открыты уровни 1 и 3 (и не важно, пройдены ли), он проходит 1, открывается только 2
        """
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        await user_season_factory(
            user_id=user_id,
            season_id=1,
        )
        # в этом тесте еще проверяем открытость второго сезона у юзера
        await user_season_factory(
            user_id=user_id,
            season_id=2,
        )

        # 1й уровень открыт у юзера, но еще не пройден
        user_level_1 = await user_level_factory(
            user_id=user_id,
            level_id=1,
            finished=False,
        )
        # 3й уровень открыт у юзера, и не важно, пройден он или нет
        user_level_3 = await user_level_factory(
            user_id=user_id,
            level_id=3,
            finished=True,
        )

        # проходит 1й уровень
        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=user_level_1.id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        response_json = response.json()

        levels = response_json["seasons"]["1"]["levels"]
        assert levels == {
            "1": {
                "user_level_id": user_level_1.id,
                "finished": True,
            },
            "2": {
                "user_level_id": 3,
                "finished": False,  # <- вот тут открылось
            },
            "3": {
                "user_level_id": user_level_3.id,
                "finished": True,
            },
        }

        levels = response_json["seasons"]["2"]["levels"]
        assert levels == {}

        # поскольку там транзакция, то по updated_at не совсем корректно смотреть
        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels ORDER BY created_at DESC""")
        assert len(user_levels) == 3  # было 2, стало 3

        assert user_levels[0]["level_id"] == 2
        assert user_levels[0]["finished"] is False  # а вот это 2й - который открылся последним по времени

        assert user_levels[1]["level_id"] == 3
        assert user_levels[1]["finished"] is True  # это 3й уровень, который не изменился

        assert user_levels[2]["finished"] is True  # 1му уровню поставилось что он пройден

    @pytest.mark.usefixtures("init_db_cards")
    @pytest.mark.asyncio
    async def test_open_related_season(
        self,
        # service fixtures
        db_connection,
        client: AsyncClient,
        user_login_fixture,
        # fixtures for test
        game_constants_factory,
        user_resource_factory,
        user_upgrades_factory,
        user_level_factory,
        user_season_factory,
        season_factory,
        level_factory,
        level_related_levels_factory,
        season_related_seasons_factory,
        leader_factory,
        card_factory,
    ):
        """
        Базовая фикстура добавила уже 4 разных уровня

        И всё, открывать новые не надо, их ведь нет
        Если уровень УЖЕ пройден, ничего страшного, так и останется
        """
        user_id = user_login_fixture["id"]
        access_token = user_login_fixture["token"]["access_token"]

        await game_constants_factory()
        await user_resource_factory(
            id=user_id,
            money=1000,
            crops=0,
            wood=500,
        )
        await user_upgrades_factory(id=user_id)

        # эти нужны для того, чтобы в наградах добавиться пользователю
        new_leader = await leader_factory(
            faction_id=1,
            ability_id=1,
            unlocked=False,
        )
        new_card_1 = await card_factory(
            faction_id=1,
            ability_id=1,
            color_id=1,
            type_id=1,
            unlocked=False,
        )
        new_card_2 = await card_factory(
            faction_id=1,
            ability_id=1,
            color_id=1,
            type_id=1,
            unlocked=False,
        )

        # у юзера открыт первый уровень первого сезона
        user_level = await user_level_factory(
            user_id=user_id,
            level_id=1,
        )
        await user_season_factory(
            user_id=user_id,
            season_id=1,
            finished=True,
        )

        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels""")
        assert len(user_levels) == 1

        # --------------- проходим 1й уровень ---------------
        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=user_level.id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        # открылись уровни 2 и 3
        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels""")
        assert len(user_levels) == 3

        # --------------- проходим уровень 2 ---------------
        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=2),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        # новых уровней пока не добавилось
        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels""")
        assert len(user_levels) == 3

        # в этом тесте создаем третий сезон, который так же связан с первым:
        season_3 = await season_factory(
            name="Season 3",
            description="Season 3",
            unlocked=False,
            data={
                "rewards": {
                    "resources": {
                        ResourceType.MONEY: 2000,
                        ResourceType.WOOD: 1000,
                        ResourceType.CROPS: 1000,
                    },
                    "cards": [new_card_1.id, new_card_2.id],
                    "leaders": [new_leader.id],
                },
            },
        )
        # два уровня для сезона 3 - только один открыт
        level_of_season_3_first = await level_factory(
            season_id=season_3.id,
            enemy_leader_id=1,
            unlocked=True,
            data={
                "rewards": {
                    "resources": {
                        ResourceType.MONEY: 1111,
                    },
                    "cards": [new_card_1.id],
                },
            },
        )
        level_of_season_3_second = await level_factory(
            season_id=season_3.id,
            enemy_leader_id=1,
            unlocked=False,
        )
        # и есть связь между уровнями нового третьего сезона
        await level_related_levels_factory(
            level_id=level_of_season_3_first.id,
            related_level_id=level_of_season_3_second.id,
        )

        # связь сезона 1 с новым сезоном 3
        await season_related_seasons_factory(
            season_id=1,
            related_season_id=season_3.id,
        )

        # --------------- вот теперь проходим уровень 3 ---------------
        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=3),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        # и вот тут открылись 2 новых сезона, а текущему проставилось finished = true
        user_seasons: list[dict] = await db_connection.fetch("""SELECT * FROM user_seasons ORDER BY updated_at""")
        assert len(user_seasons) == 3  # вот тут и добавились новый сезоны

        assert user_seasons[0]["finished"] is True  # это для первого сезона юзера
        assert user_seasons[0]["season_id"] == 1
        assert user_seasons[1]["finished"] is False  # это новый сезон!
        assert user_seasons[2]["finished"] is False  # это новый сезон!

        # добавилось 2 новых уровня! один из сезона 2 (по умолчанию) и один из сезона 3
        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels ORDER BY updated_at DESC""")
        assert len(user_levels) == 5

        # --------------- вот теперь проходим уровень 4 из сезона 2 ---------------
        # только надо найти его id
        user_level_id: int = await db_connection.fetchval(
            """
                SELECT user_levels.id FROM user_levels
                JOIN levels ON user_levels.level_id = levels.id
                WHERE levels.season_id = 2
            """,
        )

        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=user_level_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        # у 2 сезона нет связей, поэтому ему просто проставилось finished = true
        user_seasons: list[dict] = await db_connection.fetch("""SELECT * FROM user_seasons ORDER BY updated_at DESC""")
        assert len(user_seasons) == 3  # вот тут и добавился новый сезон

        assert user_seasons[0]["finished"] is True  # обновленный сезон 2
        assert user_seasons[0]["season_id"] == 2

        # и тут без изменений
        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels ORDER BY updated_at DESC""")
        assert len(user_levels) == 5

        # ИТОГО: 4 пройденных уровня (3 из сезона 1, 1 из сезона 2), 1 не пройден (из сезона 3)
        finished_levels: int = await db_connection.fetchval(
            """SELECT COUNT(*) FROM user_levels WHERE finished IS TRUE""",
        )
        assert finished_levels == 4

        # --------------- проходим уровень 5 из сезона 3 ---------------
        # только надо найти его id
        user_level_id: int = await db_connection.fetchval(
            """
                SELECT user_levels.id FROM user_levels
                JOIN levels ON user_levels.level_id = levels.id
                WHERE levels.season_id = 3
            """,
        )

        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=user_level_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        response_json = response.json()

        assert response_json["resources"] is not None
        assert response_json["cards"] is not None
        assert response_json["leaders"] is None

        # у 3 сезона нет связей
        user_seasons: list[dict] = await db_connection.fetch("""SELECT * FROM user_seasons ORDER BY updated_at DESC""")
        assert len(user_seasons) == 3

        # в сезоне 3 по тесту есть 2 уровеня, и у них есть связь, тут открылся соответственно еще один уровень
        user_levels: list[dict] = await db_connection.fetch("""SELECT * FROM user_levels ORDER BY updated_at DESC""")
        assert len(user_levels) == 6

        # но уровень-то прошли, и ему поставим finished = true
        assert user_levels[0]["finished"] is True
        assert user_levels[0]["level_id"] == level_of_season_3_first.id
        assert user_levels[0]["id"] == user_level_id

        # ИТОГО: 5 пройденных уровня (3 из сезона 1, 1 из сезона 2, 1 из сезона 3)
        finished_levels: int = await db_connection.fetchval(
            """SELECT COUNT(*) FROM user_levels WHERE finished IS TRUE""",
        )
        assert finished_levels == 5

        user_cards = await db_connection.fetch("""SELECT * FROM user_cards""")
        assert len(user_cards) == 1  # добавилась в результате награды за уровень 1 из сезона 3
        assert user_cards[0]["card_id"] == new_card_1.id
        user_leaders = await db_connection.fetch("""SELECT * FROM user_leaders""")
        assert len(user_leaders) == 0

        user_resources = await db_connection.fetchrow("""SELECT * FROM user_resources WHERE id = $1""", user_id)
        assert user_resources["money"] == 1000 + 1111  # 1000 была, 1111 добавилось за уровень 1 из сезона 3
        assert user_resources["crops"] == 0
        assert user_resources["wood"] == 500

        # --------------- и наконец проходим уровень 6 из сезона 3, он весь сезон закомплитит ---------------
        # только надо найти его id, он там один непройденный
        user_level_id: int = await db_connection.fetchval(
            """
                SELECT user_levels.id FROM user_levels
                JOIN levels ON user_levels.level_id = levels.id
                WHERE levels.season_id = 3 AND user_levels.finished IS FALSE
            """,
        )

        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=user_level_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        response_json = response.json()

        assert response_json["resources"] is not None
        assert response_json["cards"] is not None
        assert response_json["leaders"] is not None

        # все 6 уровней пройдены
        user_levels: list[dict] = await db_connection.fetch(
            """SELECT * FROM user_levels WHERE finished IS TRUE""",
        )
        assert len(user_levels) == 6

        # все 3 сезона пройдены
        user_seasons: list[dict] = await db_connection.fetch(
            """SELECT * FROM user_seasons WHERE finished IS TRUE""",
        )
        assert len(user_seasons) == 3

        user_cards = await db_connection.fetch("""SELECT * FROM user_cards ORDER BY card_id DESC""")
        assert len(user_cards) == 2  # добавилась в результате награды за весь сезон 3
        assert user_cards[0]["card_id"] == new_card_2.id
        assert user_cards[0]["count"] == 1
        assert user_cards[1]["card_id"] == new_card_1.id
        assert user_cards[1]["count"] == 2

        user_leaders = await db_connection.fetch("""SELECT * FROM user_leaders""")
        assert len(user_leaders) == 1  # добавился в результате награды за сезон 3!
        assert user_leaders[0]["leader_id"] == new_leader.id

        user_resources = await db_connection.fetchrow("""SELECT * FROM user_resources WHERE id = $1""", user_id)
        assert user_resources["money"] == 1000 + 1111 + 2000
        assert user_resources["crops"] == 0 + 1000
        assert user_resources["wood"] == 500 + 1000

        # --------------- если даже пройти сезон заново, никаких наград 2й раз не будет ---------------
        response = await client.patch(
            self.endpoint.format(user_id=user_id, user_level_id=user_level_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        response_json = response.json()

        assert response_json["resources"] is None
        assert response_json["cards"] is None
        assert response_json["leaders"] is None

        # ничего не поменялось по балансу ресурсов
        user_resources = await db_connection.fetchrow("""SELECT * FROM user_resources WHERE id = $1""", user_id)
        assert user_resources["money"] == 1000 + 1111 + 2000
        assert user_resources["crops"] == 0 + 1000
        assert user_resources["wood"] == 500 + 1000
