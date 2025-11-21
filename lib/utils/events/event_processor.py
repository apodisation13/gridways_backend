import json
from typing import Any

from lib.utils.db.pool import Database
from lib.utils.events.actions import ACTION_REGISTRY


class EventProcessor:
    def __init__(self, db: Database):
        self.db = db

    async def process_event(self, event_data: dict[str, Any]):
        event_type = event_data['event_type']
        payload = event_data['payload']
        # config_data = event_data['config']
        print("STR14!!!!!!", event_type, payload)

        # Получаем конфигурацию события из БД
        async with self.db.connection() as conn:
            event_config = await conn.fetchrow(
                """select processing::jsonb from events where type = $1""",
                event_type,
            )
            print("SRT23", type(event_config), event_config)
            processing_str = event_config['processing']
            processing = json.loads(processing_str)
        print("SRT23", type(processing), processing)

        if not event_config:
            raise ValueError(f"Event config not found for {event_type}")

        # # Создаем запись в логе
        # log_entry = EventLog(
        #     event_name=event_type,
        #     payload=payload,
        #     status="pending"
        # )
        # self.db.add(log_entry)
        # self.db.commit()

        try:
            # Выполняем действия
            execution_context = {**payload, 'event_type': event_type}
            print("STR40", execution_context)
            # actions_config = event_config.processing.get('actions', [])
            actions_config = processing
            print("STR41", actions_config)

            for action_config_data in actions_config:
                print("STR42", action_config_data)
                # action_config = ActionConfig(**action_config_data)
                await self._execute_action(
                    action_config_data,
                    action_type=action_config_data["type"],
                    context=execution_context,
                )

            # # Обновляем статус
            # log_entry.status = "success"
            # log_entry.execution_context = execution_context

        except Exception as e:
            # log_entry.status = "failed"
            # log_entry.error_message = str(e)
            print("STR48", e)
        finally:
            print("STR50!!!!!!!!!!!!!!!!!")
            # self.db.commit()

    async def _execute_action(
        self,
        action_config: dict,
        action_type: str,
        context: dict[str, Any],
    ):
        action_class = ACTION_REGISTRY.get(action_type)
        print("STR77", action_class)
        if not action_class:
            raise ValueError(f"Unknown action type: {action_type}")

        action_instance = action_class(config=action_config)  # или передавай конфиг если нужно
        success = await action_instance.execute(context=context)

        # # action = action_class(action_config.dict())
        # success = await action_class.execute(context=context)

        if not success:
            raise Exception(f"Action {action_class} execution failed")
