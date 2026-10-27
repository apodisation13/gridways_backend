import logging

import asyncpg

from lib.utils.schemas.game import ResourceType, UpgradeSubtype, UpgradeType
from services.api.app.apps.cards.schemas import Deck
from services.api.app.apps.game_const import logic as game_const_logic
from services.api.app.apps.progress.schemas import (
    CompletionRewards,
    CreateDeckRequest,
    UserCard,
    UserDeck,
    UserLeader,
    UserLevel,
    UserResources,
    UserSeason,
)
from services.api.app.exceptions.exceptions import DeckRequestError, NegativeResourcesError


logger = logging.getLogger(__name__)


def reject_deck_request(user_id: int, message: str) -> None:
    logger.error("Invalid deck request from user %s: %s", user_id, message)
    raise DeckRequestError(message)


async def validate_deck_request(
    connection: asyncpg.Connection,
    user_id: int,
    deck: CreateDeckRequest,
    creating: bool,
) -> None:
    """
    Функция валидации колоды, которую юзер хочет сохранить. Тут мы проверяем:
    1. Нет повторов в картах
    2. Проверяем, что лидер колоды открыт и доступен (есть count >= 1 в user_leaders)
    3. Проверяем, что все карты в колоде - тоже открыты у юзера (count >= 1 в user_cards)
    4. Проверяем количество карт в колоде с учетом уровня прокачки юзера
    5. При создании колоды - так же проверяем максимальный запас колод с учетом прокачки юзера
    """
    # 1. Проверяем, что нет повторяющихся карт
    if len(deck.cards) != len(set(deck.cards)):
        reject_deck_request(user_id, "A deck cannot contain duplicate cards")

    # 2. Провяряем что лидер открыт у юзера
    leader: int | None = await connection.fetchval(
        """
            SELECT
                leader_id
            FROM
                user_leaders
            WHERE
                user_id = $1
                AND leader_id = $2
                AND count >= 1
            FOR SHARE
        """,
        user_id,
        deck.leader_id,
    )
    if leader is None:
        reject_deck_request(user_id, "The selected leader is not unlocked")

    # 3. Берем все карты из запроса колоды и ищем те, которых НЕТ у юзера
    owned_cards = await connection.fetch(
        """
            SELECT
                card_id
            FROM
                user_cards
            WHERE
                user_id = $1
                AND card_id = ANY($2::int[])
                AND count >= 1
            FOR SHARE
        """,
        user_id,
        deck.cards,
    )
    unavailable = set(deck.cards) - {row["card_id"] for row in owned_cards}
    if unavailable:
        reject_deck_request(user_id, f"Cards are not unlocked: {unavailable}")

    # 4. Ищем текущий уровень двух параметров:
    # - MAX_CARDS_IN_DECK - проверяем длину колоды от уровня 0 до уровня юзера
    # - MAX_DECKS - проверяем сколько сейчас уже у юзера колод

    # 4.1. Берем все игровые константы и апгрейды из них.
    game_const = await game_const_logic.get_game_constants(connection=connection)
    game_upgrades = game_const["upgrades"][UpgradeType.GAME]["upgrades"]

    # 4.2. Ищем апгрейды юзера
    user_upgrades = await connection.fetchval(
        """
            SELECT
                data::jsonb
            FROM
                user_upgrades
            WHERE
                id = $1
            FOR SHARE
        """,
        user_id,
    )

    # 4.3. Из них берем только апгрейды для MAX_CARDS_IN_DECK, MAX_CARDS_IN_DECK
    user_game_upgrades: dict = (user_upgrades or {}).get(UpgradeType.GAME, {})

    # 4.4. Берем конфиг из game_const для типа MAX_CARDS_IN_DECK
    max_cards_in_deck_config: dict = game_upgrades[UpgradeSubtype.MAX_CARDS_IN_DECK]["upgrades"]

    # 4.5 Ищем минимальное значение и текущее для юзера
    min_cards_config: int = max_cards_in_deck_config["0"]["value"]
    max_user_cards: int = max_cards_in_deck_config[str(user_game_upgrades.get(UpgradeSubtype.MAX_CARDS_IN_DECK, 0))][
        "value"
    ]

    # 4.6. Проверяем собственно длину колоды
    if not min_cards_config <= len(deck.cards) <= max_user_cards:
        reject_deck_request(user_id, f"Deck size must be between {min_cards_config} and {max_user_cards} cards")

    # 5. Если создаем колоду, то еще надо посмотреть на текущий уровень MAX_DECKS
    if creating:
        max_decks_config = game_upgrades[UpgradeSubtype.MAX_DECKS]["upgrades"]
        max_user_decks = max_decks_config[str(user_game_upgrades.get(UpgradeSubtype.MAX_DECKS, 0))]["value"]
        current_decks = await connection.fetchval(
            """
                SELECT
                    COUNT(*)
                FROM
                    user_decks
                WHERE
                    user_id = $1
            """,
            user_id,
        )
        if current_decks >= max_user_decks:
            reject_deck_request(user_id, f"Maximum number of decks reached: {max_user_decks}")


async def get_user_seasons(
    connection: asyncpg.Connection,
    user_id: int,
) -> dict[int, UserSeason]:
    seasons = await connection.fetch(
        """
            SELECT season_id, id AS user_season_id, finished
            FROM user_seasons
            WHERE user_id = $1
            ORDER BY season_id
        """,
        user_id,
    )
    user_seasons = {
        row["season_id"]: UserSeason(
            user_season_id=row["user_season_id"],
            finished=row["finished"],
            levels={},
        )
        for row in seasons
    }
    levels = await connection.fetch(
        """
            SELECT levels.season_id, user_levels.level_id,
                user_levels.id AS user_level_id, user_levels.finished
            FROM user_levels
            JOIN levels ON levels.id = user_levels.level_id
            WHERE user_levels.user_id = $1
            ORDER BY levels.season_id, user_levels.level_id
        """,
        user_id,
    )
    for row in levels:
        season = user_seasons.get(row["season_id"])
        if season is not None:
            season.levels[row["level_id"]] = UserLevel(
                user_level_id=row["user_level_id"],
                finished=row["finished"],
            )
    return user_seasons


async def get_user_cards(
    connection: asyncpg.Connection,
    user_id: int,
) -> dict[int, UserCard]:
    user_cards: list[dict] = await connection.fetch(
        """
            SELECT
                user_cards.id AS user_card_id,
                user_cards.card_id,
                user_cards.count
            FROM
                user_cards
            WHERE
                user_cards.user_id = $1
        """,
        user_id,
    )

    return {
        row["card_id"]: UserCard(
            user_card_id=row["user_card_id"],
            count=row["count"],
        )
        for row in user_cards
    }


async def get_user_leaders(
    connection: asyncpg.Connection,
    user_id: int,
) -> dict[int, UserLeader]:
    user_leaders: list[dict] = await connection.fetch(
        """
            SELECT
                user_leaders.id AS user_leader_id,
                user_leaders.leader_id,
                user_leaders.count
            FROM
                user_leaders
            WHERE
                user_leaders.user_id = $1
        """,
        user_id,
    )

    return {
        row["leader_id"]: UserLeader(
            user_leader_id=row["user_leader_id"],
            count=row["count"],
        )
        for row in user_leaders
    }


async def construct_user_decks(
    connection: asyncpg.Connection,
    user_id: int,
) -> list[UserDeck]:
    user_decks: list[dict] = await connection.fetch(
        """
            SELECT
                user_decks.id AS user_deck_id,
                decks.id AS deck_id,
                decks.name AS deck_name,
                decks.leader_id AS leader_id,
                card_decks.card_id AS card_id,
                cards.data -> 'hp' AS card_hp,
                leaders.data -> 'hp' AS leader_hp
            FROM
                user_decks
            JOIN decks ON user_decks.deck_id = decks.id
            JOIN card_decks ON decks.id = card_decks.deck_id
            JOIN cards ON card_decks.card_id = cards.id
            JOIN leaders ON decks.leader_id = leaders.id
            WHERE
                user_decks.user_id = $1
            ORDER BY
                decks.updated_at DESC,
                decks.id DESC,
                cards.color_id DESC,
                (cards.data ->> 'damage')::int DESC,
                (cards.data ->> 'hp')::int DESC,
                (cards.data ->> 'charges')::int DESC,
                cards.id ASC;
        """,
        user_id,
    )

    user_decks_dict = {}

    for row in user_decks:
        user_deck_id = row["user_deck_id"]

        card_id: int = row["card_id"]
        card_hp = row["card_hp"]

        if user_deck_id not in user_decks_dict:
            deck_id: int = row["deck_id"]
            deck_name: str = row["deck_name"]
            leader_id: int = row["leader_id"]
            leader_hp: int = row["leader_hp"]

            user_decks_dict[user_deck_id] = UserDeck(
                user_deck_id=user_deck_id,
                deck=Deck(
                    id=deck_id,
                    name=deck_name,
                    leader_id=leader_id,
                    health=card_hp + leader_hp,  # при первом заходе сюда добавляем сразу и жизни лидера, и первой карты
                    cards=[card_id],
                ),
            )
        else:
            user_deck: UserDeck = user_decks_dict[user_deck_id]
            user_deck.deck.cards.append(card_id)
            user_deck.deck.health += card_hp

    return list(user_decks_dict.values())


async def get_user_resources(
    user_id: int,
    connection: asyncpg.Connection,
) -> UserResources:
    user_resources = await connection.fetchrow(
        """
            SELECT
                scraps,
                raw_bronze,
                raw_silver,
                raw_gold,
                bronze_ingots,
                silver_ingots,
                gold_ingots,
                crops,
                wood,
                silk,
                kegs,
                big_kegs,
                chests,
                keys,
                rare_gem,
                money,
                flowers,
                -- inventory items
                first_aid_kits,
                shields,
                immune_magics,
                draw_cards,
                mega_bombs,
                random_bombs,
                clears,
                purifies,
                random_effects
            FROM user_resources
            WHERE id = $1
        """,
        user_id,
    )
    return UserResources.get_one(user_resources)


async def change_resources(
    connection: asyncpg.Connection,
    user_id: int,
    resources_to_change: dict[ResourceType, int],
    scenario: str,
) -> UserResources:
    if any(delta > 0 for delta in resources_to_change.values()):
        current_resources: UserResources = await get_user_resources(
            connection=connection,
            user_id=user_id,
        )
        resources_to_change = await cap_resources_to_max(
            connection=connection,
            resources_to_change=resources_to_change,
            current_resources=current_resources,
            user_id=user_id,
        )

    set_parts = []
    query_params = [user_id]

    for i, (resource, delta) in enumerate(resources_to_change.items(), start=2):
        set_parts.append(f"{resource} = {resource} + ${i}")
        query_params.append(delta)

    set_parts.append("updated_at = NOW()")

    query = f"""
        UPDATE user_resources
        SET {", ".join(set_parts)}
        WHERE id = $1
        RETURNING *
    """  # noqa: S608

    result = await connection.fetchrow(query, *query_params)
    user_resources: UserResources = UserResources.get_one(result)

    await validate_non_negative_values(
        resources_to_change=resources_to_change,
        user_resources=user_resources,
        user_id=user_id,
        scenario=scenario,
    )

    return user_resources


async def validate_non_negative_values(
    resources_to_change: dict,
    user_resources: UserResources,
    user_id: int,
    scenario: str,
) -> None:
    for r in resources_to_change:
        actual_resource: int = getattr(user_resources, r)
        if actual_resource < 0:
            msg = "Scenario: %s, user_id: %s, resource: %s - insufficient resources (actual: %s)"
            logger.error(msg, scenario, user_id, r, actual_resource)
            raise NegativeResourcesError(
                msg % (scenario, user_id, r, actual_resource),
            )


async def cap_resources_to_max(
    connection: asyncpg.Connection,
    resources_to_change: dict[ResourceType, int],
    current_resources: UserResources,
    user_id: int,
) -> dict[ResourceType, int]:
    user_upgrades: dict = await connection.fetchval(
        """
            SELECT
                user_upgrades.data::jsonb
            FROM
                user_upgrades
            WHERE user_upgrades.id = $1
        """,
        user_id,
    )
    game_const: dict = await game_const_logic.get_game_constants(
        connection=connection,
    )
    upgrades_config: dict = game_const["upgrades"]

    adjusted = dict(resources_to_change)
    for resource_type, delta in resources_to_change.items():
        if delta <= 0 or resource_type == ResourceType.KEYS:
            continue

        resource_upgrade_type = UpgradeType.RESOURCES
        if resource_type == ResourceType.MONEY:
            correct_upgrade_subtype = UpgradeSubtype.MONEY
        elif resource_type == ResourceType.SCRAPS:
            correct_upgrade_subtype = UpgradeSubtype.SCRAPS
        elif resource_type == ResourceType.SILK:
            correct_upgrade_subtype = UpgradeSubtype.SILK
        elif resource_type == ResourceType.RARE_GEM:
            correct_upgrade_subtype = UpgradeSubtype.RARE_GEMS
        elif resource_type in (ResourceType.CROPS, ResourceType.WOOD):
            correct_upgrade_subtype = UpgradeSubtype.WOOD
        elif resource_type in (ResourceType.BRONZE_INGOTS, ResourceType.SILVER_INGOTS, ResourceType.GOLD_INGOTS):
            correct_upgrade_subtype = UpgradeSubtype.INGOTS
        elif resource_type in (ResourceType.RAW_BRONZE, ResourceType.RAW_SILVER, ResourceType.RAW_GOLD):
            correct_upgrade_subtype = UpgradeSubtype.RAW
        elif resource_type in (ResourceType.KEGS, ResourceType.BIG_KEGS, ResourceType.CHESTS):
            correct_upgrade_subtype = UpgradeSubtype.KEGS
        elif resource_type == ResourceType.FLOWERS:
            correct_upgrade_subtype = UpgradeSubtype.FLOWERS
        # inventory items
        elif resource_type == ResourceType.FIRST_AID_KITS:
            correct_upgrade_subtype = UpgradeSubtype.FIRST_AID_KITS
            resource_upgrade_type = UpgradeType.INVENTORY
        elif resource_type == ResourceType.SHIELDS:
            correct_upgrade_subtype = UpgradeSubtype.SHIELDS
            resource_upgrade_type = UpgradeType.INVENTORY
        elif resource_type == ResourceType.IMMUNE_MAGICS:
            correct_upgrade_subtype = UpgradeSubtype.IMMUNE_MAGICS
            resource_upgrade_type = UpgradeType.INVENTORY
        elif resource_type == ResourceType.DRAW_CARDS:
            correct_upgrade_subtype = UpgradeSubtype.DRAW_CARDS
            resource_upgrade_type = UpgradeType.INVENTORY
        elif resource_type == ResourceType.MEGA_BOMBS:
            correct_upgrade_subtype = UpgradeSubtype.MEGA_BOMBS
            resource_upgrade_type = UpgradeType.INVENTORY
        elif resource_type == ResourceType.RANDOM_BOMBS:
            correct_upgrade_subtype = UpgradeSubtype.RANDOM_BOMBS
            resource_upgrade_type = UpgradeType.INVENTORY
        elif resource_type == ResourceType.CLEARS:
            correct_upgrade_subtype = UpgradeSubtype.CLEARS
            resource_upgrade_type = UpgradeType.INVENTORY
        elif resource_type == ResourceType.PURIFIES:
            correct_upgrade_subtype = UpgradeSubtype.PURIFIES
            resource_upgrade_type = UpgradeType.INVENTORY
        elif resource_type == ResourceType.RANDOM_EFFECTS:
            correct_upgrade_subtype = UpgradeSubtype.RANDOM_EFFECTS
            resource_upgrade_type = UpgradeType.INVENTORY
        else:
            raise ValueError(f"Unknown resource type for max cap: {resource_type}")

        # почему тут 0 по умолчанию - если апгрейд новый (добавленный недавно), его еще нет у юзера, берем 0 тогда
        user_upgrade_level: int = user_upgrades[resource_upgrade_type].get(correct_upgrade_subtype, 0)
        level_data: dict = upgrades_config[resource_upgrade_type]["upgrades"][correct_upgrade_subtype]["upgrades"][
            str(user_upgrade_level)
        ]
        max_value: int = level_data["value"]

        current_value: int = getattr(current_resources, resource_type)
        adjusted[resource_type] = min(delta, max(0, max_value - current_value))

    return adjusted


async def open_default_content(
    connection: asyncpg.Connection,
    user_id: int,
):
    logger.info("Opening default content for user: %s", user_id)

    # 1. берем все открытые по умолчанию карты
    cards = await connection.fetch("""SELECT cards.id FROM cards WHERE cards.unlocked IS TRUE""")
    logger.info("Number of default cards to insert: %s", len(cards))

    # 2. инзертим их юзеру
    user_cards = await connection.fetch(
        """
            INSERT INTO user_cards (user_id, card_id, count)
            SELECT $1, s.card_id, 1
            FROM unnest($2::int[]) AS s(card_id)
            RETURNING id
        """,
        user_id,
        [card["id"] for card in cards],
    )
    logger.info("Number of user_cards inserted: %s", len(user_cards))

    if len(user_cards) != len(cards):
        msg = "Number of unlocked cards %s does not match number of inserted user_cards %"
        logger.error(msg, len(cards), len(user_cards))
        raise Exception(msg % (len(cards), len(user_cards)))

    # 3. берем всех открытых по умолчанию лидеров
    leaders = await connection.fetch("""SELECT leaders.id FROM leaders WHERE leaders.unlocked IS TRUE""")
    logger.info("Number of default leaders to insert: %s", len(leaders))

    # 4. инзертим их юзеру
    user_leaders = await connection.fetch(
        """
            INSERT INTO user_leaders (user_id, leader_id, count)
            SELECT $1, s.leader_id, 1
            FROM unnest($2::int[]) AS s(leader_id)
            RETURNING id
        """,
        user_id,
        [card["id"] for card in leaders],
    )
    logger.info("Number of user_leaders inserted: %s", len(user_leaders))

    if len(user_leaders) != len(leaders):
        msg = "Number of unlocked leaders %s does not match number of inserted user_leaders %s"
        logger.error(msg, len(leaders), len(user_leaders))
        raise Exception(msg % (len(leaders), len(user_leaders)))

    # 5. инзертим юзеру base-desk
    await connection.execute(
        """
            INSERT INTO user_decks
            (user_id, deck_id)
            VALUES ($1, 1)
        """,
        user_id,
    )
    logger.info("Inserted user_desk for base-deck")

    # 6. берем все открытые по умолчанию уровни
    levels = await connection.fetch("""SELECT levels.id FROM levels WHERE levels.unlocked IS TRUE""")
    logger.info("Number of default levels to insert: %s", len(levels))

    # 7. инзертим их юзеру
    user_levels = await connection.fetch(
        """
            INSERT INTO user_levels (user_id, level_id)
            SELECT $1, s.level_id
            FROM unnest($2::int[]) AS s(level_id)
            RETURNING id
        """,
        user_id,
        [level["id"] for level in levels],
    )
    logger.info("Number of user_levels inserted: %s", len(user_levels))

    if len(user_levels) != len(levels):
        msg = "Number of unlocked levels %s does not match number of inserted user_levels %s"
        logger.error(msg, len(levels), len(user_levels))
        raise Exception(msg % (len(levels), len(user_levels)))

    # 8. берем все открытые по умолчанию сезоны
    seasons = await connection.fetch("""SELECT seasons.id FROM seasons WHERE seasons.unlocked IS TRUE""")
    logger.info("Number of default seasons to insert: %s", len(seasons))

    # 9. инзертим их юзеру
    user_seasons = await connection.fetch(
        """
            INSERT INTO user_seasons (user_id, season_id)
            SELECT $1, s.season_id
            FROM unnest($2::int[]) AS s(season_id)
            RETURNING id
        """,
        user_id,
        [season["id"] for season in seasons],
    )
    logger.info("Number of user_seasons inserted: %s", len(user_seasons))

    if len(user_seasons) != len(seasons):
        msg = "Number of unlocked seasons %s does not match number of inserted user_seasons %s"
        logger.error(msg, len(seasons), len(user_seasons))
        raise Exception(msg % (len(seasons), len(user_seasons)))

    # 10. создаем юзеру дефолтные ресурсы - они указаны напрямую в БД
    await connection.execute("""INSERT INTO user_resources (id) VALUES ($1)""", user_id)

    logger.info("Finished creating user database for user %s", user_id)


async def grant_bonus_cards(
    connection: asyncpg.Connection,
    user_id: int,
    cards_ids: list[int],
) -> None:
    await connection.execute(
        """
            WITH counts AS (
                SELECT card_id, COUNT(*) AS count
                FROM unnest($2::int[]) AS card_id
                GROUP BY card_id
            )
            INSERT INTO user_cards (user_id, card_id, count)
            SELECT $1, card_id, count FROM counts ORDER BY card_id
            ON CONFLICT (user_id, card_id)
            DO UPDATE SET count = user_cards.count + EXCLUDED.count, updated_at = NOW()
        """,
        user_id,
        cards_ids,
    )


async def grant_bonus_leaders(
    connection: asyncpg.Connection,
    user_id: int,
    leaders_ids: list[int],
) -> None:
    await connection.execute(
        """
            WITH counts AS (
                SELECT leader_id, COUNT(*) AS count
                FROM unnest($2::int[]) AS leader_id
                GROUP BY leader_id
            )
            INSERT INTO user_leaders (user_id, leader_id, count)
            SELECT $1, leader_id, count FROM counts ORDER BY leader_id
            ON CONFLICT (user_id, leader_id)
            DO UPDATE SET count = user_leaders.count + EXCLUDED.count, updated_at = NOW()
        """,
        user_id,
        leaders_ids,
    )


async def grant_completion_rewards(
    connection: asyncpg.Connection,
    user_id: int,
    rewards: list[dict],
    scenario: str,
) -> dict:
    if not rewards:
        return {}

    logger.info("Completing rewards for user %s, rewards %s, scenario %s", user_id, rewards, scenario)
    cards_ids = []
    leaders_ids = []
    resources = {}

    for data in rewards:
        reward = CompletionRewards.model_validate(data)
        cards_ids.extend(reward.cards)
        leaders_ids.extend(reward.leaders)
        for resource, amount in reward.resources.items():
            if amount:
                resources[resource] = resources.get(resource, 0) + amount

    updates = {}

    if resources:
        updates["resources"] = await change_resources(
            connection=connection,
            user_id=user_id,
            resources_to_change=resources,
            scenario=scenario,
        )

    if cards_ids:
        await grant_bonus_cards(connection=connection, user_id=user_id, cards_ids=cards_ids)
        updates["cards"] = await get_user_cards(connection=connection, user_id=user_id)

    if leaders_ids:
        await grant_bonus_leaders(connection=connection, user_id=user_id, leaders_ids=leaders_ids)
        updates["leaders"] = await get_user_leaders(connection=connection, user_id=user_id)

    return updates
