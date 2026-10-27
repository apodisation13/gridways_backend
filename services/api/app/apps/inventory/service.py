import logging

from lib.utils.db.pool import Database
from lib.utils.schemas.game import ResourceType, UpgradeSubtype, UpgradeType
from services.api.app.apps.game_const import logic as game_const_logic
from services.api.app.config import Config
from services.api.app.exceptions.exceptions import PatchInventoryProcessError


logger = logging.getLogger(__name__)


class InventoryService:
    def __init__(
        self,
        db_pool: Database,
        config: Config,
    ):
        self.db_pool = db_pool
        self.config = config

    async def get_inventory(
        self,
        user_id: int,
    ) -> dict:
        async with self.db_pool.connection() as connection:
            inventory: dict | None = await connection.fetchval(
                """
                    SELECT
                        user_inventory.data::jsonb
                    FROM
                        user_inventory
                    WHERE user_inventory.id = $1
                """,
                user_id,
            )

            if not inventory:
                logger.info("User %s inventory not found, gotta insert new", user_id)
                inventory = await connection.fetchval(
                    """
                        INSERT INTO user_inventory
                        (
                            id,
                            data
                        )
                        VALUES ($1, $2)
                        RETURNING
                            data::jsonb
                    """,
                    user_id,
                    {"slots": []},
                )

        return inventory

    async def change_inventory(
        self,
        user_id: int,
        slots: list[str],
    ) -> dict:
        # если вдруг пришли повторы слотов
        if len(set(slots)) != len(slots):
            msg = "Wrong slots %s for user %s"
            logger.error(msg, slots, user_id)
            raise PatchInventoryProcessError(msg % (slots, user_id))

        # если слоты не из списка разрешенных
        for slot in slots:
            if slot not in ResourceType.inventory_resources():
                msg = "Wrong slot: %s, for user %s"
                logger.error(msg, slot, user_id)
                raise PatchInventoryProcessError(msg % (slot, user_id))

        async with self.db_pool.transaction() as connection:
            # а здесь мы ищем сколько слотов доступно для юзера - из апгрейдов и констант
            game_const: dict = await game_const_logic.get_game_constants(connection=connection)
            slots_config: dict = game_const["upgrades"][UpgradeType.INVENTORY]["upgrades"][
                UpgradeSubtype.INVENTORY_SLOTS
            ]["upgrades"]
            user_upgrades: dict = await connection.fetchval(
                """
                    SELECT data::jsonb
                    FROM user_upgrades
                    WHERE id = $1
                    FOR SHARE
                """,
                user_id,
            )
            inventory_upgrades: dict = (user_upgrades or {}).get(UpgradeType.INVENTORY, {})
            upgrade_level: int = inventory_upgrades.get(UpgradeSubtype.INVENTORY_SLOTS, 0)
            max_slots: int = slots_config[str(upgrade_level)]["value"]

            if len(slots) > max_slots:
                msg = "Too many inventory slots for user %s: got %s, maximum %s"
                logger.error(msg, user_id, len(slots), max_slots)
                raise PatchInventoryProcessError(msg % (user_id, len(slots), max_slots))

            return await connection.fetchval(
                """
                    UPDATE
                        user_inventory
                    SET
                        data = jsonb_set(data, '{slots}', $2::jsonb),
                        updated_at = NOW()
                    WHERE
                        user_inventory.id = $1
                    RETURNING
                        data::jsonb
                """,
                user_id,
                slots,
            )
