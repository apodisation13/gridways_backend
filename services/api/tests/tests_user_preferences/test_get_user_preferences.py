import pytest

from services.api.app.apps.preferences import logic
from services.api.app.apps.preferences.schemas import DEFAULT_PREFERENCES


class TestGetUserPreferences:
    @pytest.mark.asyncio
    async def test_get_non_existing_preferences(
        self,
        # service fixtures
        db_connection,
        # fixtures for test
        user_factory,
    ):
        """
        Тут у юзера еще нет сохраненных настроек, и мы заинзертим ему новых (дефолтных)
        """
        user = await user_factory()
        user_id = user.id

        result = await logic.get_user_preferences(db_connection, user_id)
        response_json = result.model_dump()
        assert response_json == {"data": DEFAULT_PREFERENCES}

        stored = await db_connection.fetchval(
            "SELECT data::jsonb FROM user_preferences WHERE id = $1",
            user_id,
        )
        assert stored == response_json["data"]
        assert await logic.get_user_preferences(db_connection, user_id) == result

    @pytest.mark.asyncio
    async def test_get_already_existing_preferences(
        self,
        # service fixtures
        db_connection,
        # fixtures for test
        user_factory,
        user_preferences_factory,
    ):
        """
        А тут у юзера уже есть какие-то настройки, соответственно вернутся они
        """
        user = await user_factory()
        user_id = user.id

        preferences = DEFAULT_PREFERENCES.copy()
        preferences.update(
            {
                "sound_on": False,
                "move_timeout": 100,
            },
        )

        await user_preferences_factory(
            id=user_id,
            data=preferences,
        )

        result = await logic.get_user_preferences(db_connection, user_id)
        response_json = result.model_dump()
        assert response_json == {"data": preferences}

        stored = await db_connection.fetchval(
            "SELECT data::jsonb FROM user_preferences WHERE id = $1",
            user_id,
        )
        assert stored == response_json["data"]
        assert await logic.get_user_preferences(db_connection, user_id) == result
