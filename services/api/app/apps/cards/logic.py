import asyncpg

from services.api.app.apps.cards.schemas import (
    Card,
    Enemy,
    EnemyLeader,
    Leader,
    Level,
    LevelRelatedLevel,
    Season,
    SeasonRelatedSeason,
)


async def get_enemies(
    connection: asyncpg.Connection,
    base_url: str,
) -> dict[int, Enemy]:
    enemies = await connection.fetch(
        """
            SELECT
                enemies.id,
                enemies.name,

                factions.name AS faction_name,
                colors.name AS color_name,

                moves.name AS move_name,
                moves.description AS move_description,

                enemy_passive_abilities.name AS passive_ability_name,
                enemy_passive_abilities.description AS passive_ability_description,

                deathwishes.name AS deathwish_name,
                deathwishes.description AS deathwish_description,

                enemies.data,
                enemies.image_original AS image
            FROM
                enemies
            JOIN
                factions ON enemies.faction_id = factions.id
            JOIN
                colors ON enemies.color_id = colors.id
            JOIN
                moves ON enemies.move_id = moves.id
            LEFT JOIN
                deathwishes ON enemies.deathwish_id = deathwishes.id
            LEFT JOIN
                enemy_passive_abilities ON enemies.passive_ability_id = enemy_passive_abilities.id
            ORDER BY
                enemies.faction_id,
                enemies.data ->> 'hp' DESC,
                enemies.data ->> 'damage' DESC
        """,
    )

    return {row["id"]: Enemy.get_one(row, base_url) for row in enemies}


async def get_enemy_leaders(
    connection: asyncpg.Connection,
    base_url: str,
) -> dict[int, EnemyLeader]:
    enemy_leaders = await connection.fetch(
        """
            SELECT
                enemy_leaders.id,
                enemy_leaders.name,

                factions.name AS faction_name,

                enemy_leader_abilities.name AS ability_name,
                enemy_leader_abilities.description AS ability_description,

                enemy_passive_abilities.name AS passive_ability_name,
                enemy_passive_abilities.description AS passive_ability_description,

                deathwishes.name AS deathwish_name,
                deathwishes.description AS deathwish_description,

                enemy_leaders.data,
                enemy_leaders.image_original AS image
            FROM
                enemy_leaders
            JOIN
                factions ON enemy_leaders.faction_id = factions.id
            LEFT JOIN
                enemy_leader_abilities ON enemy_leaders.ability_id = enemy_leader_abilities.id
            LEFT JOIN
                enemy_passive_abilities ON enemy_leaders.passive_ability_id = enemy_passive_abilities.id
            LEFT JOIN
                deathwishes ON enemy_leaders.deathwish_id = deathwishes.id
        """,
    )

    return {row["id"]: EnemyLeader.get_one(row, base_url) for row in enemy_leaders}


async def get_leaders(
    connection: asyncpg.Connection,
    base_url: str,
) -> list[Leader]:
    leaders: list[dict] = await connection.fetch(
        """
            SELECT
                leaders.id,
                leaders.name,
                leaders.unlocked,

                factions.name AS faction_name,

                abilities.name AS ability_name,
                abilities.description AS ability_description,

                passive_abilities.name AS passive_ability_name,
                passive_abilities.description AS passive_ability_description,

                leaders.data,
                leaders.image_original AS image,
                leaders.newly_added
            FROM
                leaders
            JOIN
                factions ON leaders.faction_id = factions.id
            JOIN
                abilities ON leaders.ability_id = abilities.id
            LEFT JOIN
                passive_abilities ON leaders.passive_ability_id = passive_abilities.id
            ORDER BY
                leaders.faction_id,
                (leaders.data ->> 'hp')::int DESC,
                (leaders.data ->> 'charges')::int DESC
        """,
    )

    return [Leader.get_one(row, base_url) for row in leaders]


async def get_cards(
    connection: asyncpg.Connection,
    base_url: str,
) -> list[Card]:
    cards: list[dict] = await connection.fetch(
        """
            SELECT
                cards.id,
                cards.name,
                cards.unlocked,

                factions.name AS faction_name,
                colors.name AS color_name,
                types.name AS type_name,

                abilities.name AS ability_name,
                abilities.description AS ability_description,

                passive_abilities.name AS passive_ability_name,
                passive_abilities.description AS passive_ability_description,

                cards.data,
                cards.image_original AS image,
                cards.newly_added
            FROM
                cards
            JOIN
                factions ON cards.faction_id = factions.id
            JOIN
                colors ON cards.color_id = colors.id
            JOIN
                types ON cards.type_id = types.id
            JOIN
                abilities ON cards.ability_id = abilities.id
            LEFT JOIN
                passive_abilities ON cards.passive_ability_id = passive_abilities.id
            ORDER BY
                cards.color_id DESC,
                (cards.data ->> 'damage')::int DESC,
                (cards.data ->> 'hp')::int DESC,
                (cards.data ->> 'charges')::int DESC
        """,
    )

    return [Card.get_one(row, base_url) for row in cards]


async def get_seasons(
    connection: asyncpg.Connection,
) -> list:
    return await connection.fetch(
        """
            SELECT
                seasons.id AS season_id,
                seasons.name AS season_name,
                seasons.description AS season_description,
                seasons.x AS season_x,
                seasons.y AS season_y,
                seasons.data AS season_data,
                levels.id AS level_id,
                levels.name AS level_name,
                levels.difficulty,
                levels.starting_enemies_number,
                levels.x,
                levels.y,
                levels.data AS level_data,
                levels.enemy_leader_id AS enemy_leader_id,
                level_enemies.enemy_id AS enemy_id
            FROM seasons
            JOIN levels ON seasons.id = levels.season_id
            JOIN level_enemies ON levels.id = level_enemies.level_id
            ORDER BY seasons.id, levels.id;
        """,
    )


async def get_level_related_levels(
    connection: asyncpg.Connection,
    level_ids: set[int],
) -> dict[int, list[LevelRelatedLevel]]:
    # возвращает словарь, где ключ это id уровня, значение - список его связей (даже если связей нет)
    all_related_levels = await connection.fetch(
        """
            SELECT
                levels.id,
                level_related_levels.related_level_id,
                level_related_levels.line,
                level_related_levels.connection
            FROM levels
            LEFT JOIN level_related_levels ON levels.id = level_related_levels.level_id
            WHERE levels.id = ANY ($1)
        """,
        level_ids,
    )

    level_ids_dict = {}
    for row in all_related_levels:
        level_id = row["id"]
        level_related_level = LevelRelatedLevel(
            line=row["line"],
            connection=row["connection"],
            related_level_id=row["related_level_id"],
        )
        if level_id not in level_ids_dict:
            level_ids_dict[level_id] = [level_related_level]
        else:
            level_ids_dict[level_id].append(level_related_level)

    return level_ids_dict


async def get_season_related_seasons(
    connection: asyncpg.Connection,
    season_ids: set[int],
) -> dict[int, list[SeasonRelatedSeason]]:
    # возвращает словарь, где ключ это id сезона, значение - список его связей (даже если связей нет)
    all_related_seasons = await connection.fetch(
        """
            SELECT
                seasons.id,
                season_related_seasons.related_season_id,
                season_related_seasons.line,
                season_related_seasons.connection
            FROM seasons
            LEFT JOIN season_related_seasons ON season_related_seasons.season_id = seasons.id
            WHERE seasons.id = ANY ($1)
        """,
        season_ids,
    )

    season_ids_dict = {}
    for row in all_related_seasons:
        season_id = row["id"]
        season_related_season = SeasonRelatedSeason(
            line=row["line"],
            connection=row["connection"],
            related_season_id=row["related_season_id"],
        )
        if season_id not in season_ids_dict:
            season_ids_dict[season_id] = [season_related_season]
        else:
            season_ids_dict[season_id].append(season_related_season)

    return season_ids_dict


async def construct_seasons(
    connection: asyncpg.Connection,
) -> dict[int, Season]:
    rows = await get_seasons(connection)
    level_related_levels = await get_level_related_levels(
        connection,
        {row["level_id"] for row in rows},
    )
    season_related_seasons = await get_season_related_seasons(
        connection,
        {row["season_id"] for row in rows},
    )
    seasons: dict[int, Season] = {}
    levels: dict[int, Level] = {}
    for row in rows:
        season_id = row["season_id"]
        level_id = row["level_id"]
        if season_id not in seasons:
            seasons[season_id] = Season(
                id=season_id,
                name=row["season_name"],
                description=row["season_description"],
                x=row["season_x"],
                y=row["season_y"],
                data=row["season_data"],
                levels=[],
                children=season_related_seasons[season_id],
            )
        if level_id not in levels:
            level = Level(
                id=level_id,
                name=row["level_name"],
                difficulty=row["difficulty"],
                starting_enemies_number=row["starting_enemies_number"],
                x=row["x"],
                y=row["y"],
                data=row["level_data"],
                enemy_leader=row["enemy_leader_id"],
                enemies=[],
                children=level_related_levels[level_id],
            )
            levels[level_id] = level
            seasons[season_id].levels.append(level)
        levels[level_id].enemies.append(row["enemy_id"])
    return seasons
