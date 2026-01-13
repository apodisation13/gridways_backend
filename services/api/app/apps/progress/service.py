import asyncpg

from lib.utils.db.pool import Database
from lib.utils.schemas.game import ResourceActionSubtype, LevelDifficulty, ResourceType
from services.api.app.apps.cards.schemas import Card
from services.api.app.apps.progress.logic import process_enemies, process_cards
from services.api.app.apps.progress.schemas import (
    UserDatabase,
    UserProgressResponse,
    UserResources, CreateDeckRequest, ListDecksResponse, ResourcesRequest,
)
from services.api.app.config import Config


class UserProgressService:
    def __init__(
        self,
        db_pool: Database,
        config: Config,
    ):
        self.db_pool = db_pool
        self.config = config

    async def get_user_progress(
        self,
        user_id: int,
        base_url: str,
    ) -> UserProgressResponse:
        async with self.db_pool.connection() as connection:
            user_resources: UserResources = await self._get_user_resources(
                connection=connection,
                user_id=user_id,
            )

            game_constants: dict = await self._get_game_constants(
                connection=connection,
            )

            enemies, enemy_leaders, seasons = await process_enemies(
                connection=connection,
                user_id=user_id,
                base_url=base_url,
            )

            user_cards, user_leaders, user_decks = await process_cards(
                connection=connection,
                user_id=user_id,
                base_url=base_url,
            )

        return UserProgressResponse(
            user_database=UserDatabase(
                cards=user_cards,
                leaders=user_leaders,
                decks=user_decks,
            ),
            resources=user_resources,
            seasons=seasons,
            game_const=game_constants,
            enemies=enemies,
            enemy_leaders=enemy_leaders,
        )

    async def _get_user_resources(
        self,
        user_id: int,
        connection: asyncpg.Connection,
    ) -> UserResources:
        user_resources = await connection.fetchrow(
            """
                SELECT scraps, kegs, big_kegs, chests, wood, keys
                FROM user_resources
                WHERE id = $1
            """,
            user_id,
        )
        return UserResources(
            scraps=user_resources["scraps"],
            kegs=user_resources["kegs"],
            big_kegs=user_resources["big_kegs"],
            chests=user_resources["chests"],
            wood=user_resources["wood"],
            keys=user_resources["keys"],
        )

    async def _get_game_constants(
        self,
        connection: asyncpg.Connection,
    ) -> dict:
        game_constants: dict = await connection.fetchval("""SELECT data::jsonb FROM game_constants""")
        print(type(game_constants), game_constants)
        return game_constants

    async def create_user_deck(
        self,
        user_id: int,
        deck: CreateDeckRequest,
        base_url: str,
    ) -> ListDecksResponse:
        async with self.db_pool.transaction() as connection:
            deck_id = await connection.fetchval(
                """
                    INSERT INTO decks
                    (name, leader_id)
                    VALUES ($1, $2)
                    RETURNING id
                """,
                deck.deck_name,
                deck.leader_id,
            )
            print("STR110", deck_id)

            card_decks: list[tuple[deck_id, Card.id]] = [(deck_id, card_id) for card_id in deck.cards]
            print("STR111", card_decks)

            await connection.executemany(
                """
                INSERT INTO card_decks
                (deck_id, card_id)
                VALUES ($1, $2)
                """,
                card_decks,
            )

            await connection.execute(
                """
                INSERT INTO user_decks
                (user_id, deck_id)
                VALUES ($1, $2)
                """,
                user_id,
                deck_id,
            )

            _, _, user_decks = await process_cards(
                connection=connection,
                user_id=user_id,
                base_url=base_url,
            )
            print("STR121", len(user_decks))

        return ListDecksResponse(
            decks=user_decks,
        )

    async def delete_user_deck(
        self,
        user_id: int,
        deck_id: int,
        base_url: str,
    ) -> ListDecksResponse:
        async with self.db_pool.transaction() as connection:
            await connection.execute(
                """
                DELETE FROM user_decks
                WHERE 
                    user_decks.user_id = $1
                    AND user_decks.deck_id = $2
                """,
                user_id,
                deck_id,
            )
            await connection.execute(
                """
                DELETE FROM card_decks
                WHERE 
                    card_decks.deck_id = $1
                """,
                deck_id,
            )
            await connection.execute(
                """
                DELETE FROM decks
                WHERE 
                    decks.id = $1
                """,
                deck_id,
            )
            _, _, user_decks = await process_cards(
                connection=connection,
                user_id=user_id,
                base_url=base_url,
            )
            print("STR183", len(user_decks))

        return ListDecksResponse(
            decks=user_decks,
        )

    async def patch_user_deck(
        self,
        user_id: int,
        deck_id: int,
        deck: CreateDeckRequest,
        base_url: str,
    ) -> ListDecksResponse:
        async with self.db_pool.transaction() as connection:
            await connection.fetchrow(
                """
                    UPDATE decks
                    SET 
                        name = $2, 
                        leader_id = $3
                    WHERE
                        decks.id = $1
                """,
                deck_id,
                deck.deck_name,
                deck.leader_id,
            )

            await connection.execute(
                """
                    DELETE FROM card_decks
                    WHERE card_decks.deck_id = $1
                """,
                deck_id,
            )

            card_decks: list[tuple[deck_id, Card.id]] = [(deck_id, card_id) for card_id in deck.cards]
            print("STR220", card_decks)
            await connection.executemany(
                """
                INSERT INTO card_decks
                (deck_id, card_id)
                VALUES ($1, $2)
                """,
                card_decks,
            )

            _, _, user_decks = await process_cards(
                connection=connection,
                user_id=user_id,
                base_url=base_url,
            )
            print("STR235", len(user_decks))

        return ListDecksResponse(
            decks=user_decks,
        )

    async def manage_resources(
        self,
        user_id: int,
        resource_request: ResourcesRequest
    ) -> UserResources:

        subtype: ResourceActionSubtype = resource_request.subtype

        match subtype:
            case subtype.START_SEASON_LEVEL:
                """ { subtype: start_game, data: {level_id: int}} """
                level_id: int = resource_request.data["level_id"]

                async with self.db_pool.connection() as connection:
                    difficulty: LevelDifficulty = await connection.fetchval(
                        """
                            SELECT difficulty 
                            FROM levels
                            WHERE levels.id = $1
                        """,
                        level_id,
                    )

                    game_constants: dict = await self._get_game_constants(
                        connection=connection,
                    )

                    if difficulty == LevelDifficulty.EASY:
                        pay_resources = {ResourceType.WOOD: game_constants["play_level_easy"]}
                    elif difficulty == LevelDifficulty.NORMAL:
                        pay_resources = {ResourceType.WOOD: game_constants["play_level_normal"]}
                    elif difficulty == LevelDifficulty.HARD:
                        pay_resources = {ResourceType.WOOD: game_constants["play_level_hard"]}
                    else:
                        raise TypeError(f"Invalid level difficulty {difficulty}")

                    user_resources: UserResources = await self._get_user_resources(
                        connection=connection,
                        user_id=user_id,
                    )
                    print(level_id, difficulty, user_resources, pay_resources)

                    self._validate_user_resources_payment(
                        resources_to_change=pay_resources,
                        current_resources=user_resources,
                    )

                    return await self._change_resources(
                        connection=connection,
                        user_id=user_id,
                        resources_to_change=pay_resources,
                    )

            case subtype.WIN_SEASON_LEVEL:
                async with self.db_pool.connection() as connection:
                    return await self._change_resources(
                        connection=connection,
                        user_id=user_id,
                        resources_to_change=resource_request.data,
                    )

    def _validate_user_resources_payment(
        self,
        resources_to_change: dict[ResourceType: int],
        current_resources: UserResources,
    ) -> None:
        for resource_type, value_to_pay in resources_to_change.items():
            if getattr(current_resources, resource_type) + value_to_pay < 0:
                raise ValueError(f"Cannot pay resource {resource_type}, would be less than 0")

    async def _change_resources(
        self,
        connection: asyncpg.Connection,
        user_id: int,
        resources_to_change: dict[ResourceType: int],
    ) -> UserResources:
        set_parts = []
        query_params = [user_id]

        for i, (resource, delta) in enumerate(resources_to_change.items(), start=2):
            set_parts.append(f"{resource} = {resource} + ${i}")
            query_params.append(delta)

        query = f"""
            UPDATE user_resources
            SET {', '.join(set_parts)}
            WHERE id = $1
            RETURNING *
        """

        result = await connection.fetchrow(query, *query_params)
        return UserResources(
            wood=result["wood"],
            scraps=result["scraps"],
            kegs=result["kegs"],
            big_kegs=result["big_kegs"],
            chests=result["chests"],
            keys=result["keys"],
        )
