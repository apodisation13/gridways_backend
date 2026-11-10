import pytest

from services.api.app.apps.achievements import logic


class TestGetUserAchievements:
    @pytest.mark.asyncio
    async def test_get_non_existing_achievements(
        self,
        # service fixtures
        db_connection,
        # fixtures for test
        user_factory,
    ):
        user = await user_factory()

        result = await logic.get_user_achievements(db_connection, user.id)

        assert result == {}
        stored = await db_connection.fetchval(
            "SELECT progress::jsonb FROM user_achievements WHERE id = $1",
            user.id,
        )
        assert stored == {}
        assert await logic.get_user_achievements(db_connection, user.id) == result

    @pytest.mark.asyncio
    async def test_get_existing_achievements(
        self,
        # service fixtures
        db_connection,
        # fixtures for test
        user_factory,
        user_achievements_factory,
    ):
        user = await user_factory()
        progress = {"permanent": {"first_win": 1}, "daily": {}, "weekly": {}}
        await user_achievements_factory(
            id=user.id,
            progress=progress,
        )

        result = await logic.get_user_achievements(db_connection, user.id)

        assert result == progress
        stored = await db_connection.fetchval(
            "SELECT progress::jsonb FROM user_achievements WHERE id = $1",
            user.id,
        )
        assert stored == progress
        assert await logic.get_user_achievements(db_connection, user.id) == result
